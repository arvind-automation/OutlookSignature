from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from app.auth import (
    current_user,
    get_or_create_local_user,
    get_or_create_sso_user,
    is_admin,
    login_user_session,
    logout_user_session,
    set_team,
    write_audit,
)
from app.config import Config
from app.microsoft_sso import (
    build_auth_url,
    claims_email,
    claims_names,
    exchange_code_for_token,
    fetch_graph_profile,
    microsoft_sso_enabled,
    new_oauth_state,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not session.get("team"):
        return redirect(url_for("auth.team"))
    return redirect(url_for("generator.generator"))


@auth_bp.route("/login", methods=["GET"])
def login():
    user = current_user()
    if user:
        if session.get("team"):
            return redirect(url_for("generator.generator"))
        return redirect(url_for("auth.team"))

    return render_template(
        "login.html",
        microsoft_sso_enabled=microsoft_sso_enabled(),
        local_dev_login_enabled=current_app.config["LOCAL_DEV_LOGIN_ENABLED"],
    )


@auth_bp.post("/auth/local")
def local_login():
    if not current_app.config["LOCAL_DEV_LOGIN_ENABLED"] or microsoft_sso_enabled():
        abort(404)

    user = current_user()
    if not user:
        user = get_or_create_local_user(current_app.config["LOCAL_DEV_EMAIL"])
        login_user_session(user)
    return redirect(url_for("auth.team"))


@auth_bp.route("/auth/microsoft")
def microsoft_login():
    if not microsoft_sso_enabled():
        flash("Microsoft sign-in is not configured.", "error")
        return redirect(url_for("auth.login"))

    if current_user():
        return redirect(url_for("auth.team"))

    state = new_oauth_state()
    session["ms_oauth_state"] = state
    try:
        return redirect(build_auth_url(state))
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Failed to start Microsoft SSO")
        write_audit("login_failed", details={"reason": "sso_start_failed", "method": "microsoft"})
        flash("Could not start Microsoft sign-in. Check Azure configuration.", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/auth/microsoft/callback")
def microsoft_callback():
    if not microsoft_sso_enabled():
        flash("Microsoft sign-in is not configured.", "error")
        return redirect(url_for("auth.login"))

    error = request.args.get("error")
    if error:
        desc = request.args.get("error_description") or error
        write_audit(
            "login_failed",
            details={"reason": "sso_provider_error", "method": "microsoft", "error": error},
        )
        flash(f"Microsoft sign-in was cancelled or failed ({desc}).", "error")
        return redirect(url_for("auth.login"))

    state = request.args.get("state") or ""
    expected = session.pop("ms_oauth_state", None)
    if not expected or state != expected:
        write_audit("login_failed", details={"reason": "sso_bad_state", "method": "microsoft"})
        flash("Microsoft sign-in failed security validation. Please try again.", "error")
        return redirect(url_for("auth.login"))

    code = request.args.get("code") or ""
    if not code:
        write_audit("login_failed", details={"reason": "sso_missing_code", "method": "microsoft"})
        flash("Microsoft sign-in did not return an authorization code.", "error")
        return redirect(url_for("auth.login"))

    try:
        result = exchange_code_for_token(code)
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Microsoft token exchange failed")
        write_audit("login_failed", details={"reason": "sso_token_exchange", "method": "microsoft"})
        flash("Could not complete Microsoft sign-in. Please try again.", "error")
        return redirect(url_for("auth.login"))

    if "error" in result:
        write_audit(
            "login_failed",
            details={
                "reason": "sso_token_error",
                "method": "microsoft",
                "error": result.get("error"),
            },
        )
        flash(result.get("error_description") or "Microsoft sign-in failed.", "error")
        return redirect(url_for("auth.login"))

    claims = result.get("id_token_claims") or {}
    email = claims_email(claims)
    first_name, last_name = claims_names(claims)

    prefill: dict = {}
    access_token = result.get("access_token") or ""
    if access_token:
        try:
            prefill = fetch_graph_profile(access_token) or {}
        except Exception:  # noqa: BLE001
            current_app.logger.exception("Graph profile fetch failed; continuing SSO login")
            prefill = {}

    if prefill.get("firstName"):
        first_name = prefill["firstName"]
    if prefill.get("lastName"):
        last_name = prefill["lastName"]
    if prefill.get("email"):
        email = prefill["email"]

    user, err = get_or_create_sso_user(email, first_name=first_name, last_name=last_name)
    if not user:
        flash(err or "Microsoft sign-in failed.", "error")
        return redirect(url_for("auth.login"))

    login_user_session(user)
    if prefill:
        # Must set after login_user_session (which clears the session).
        session["profile_prefill"] = prefill
    return redirect(url_for("auth.team"))


@auth_bp.route("/team", methods=["GET", "POST"])
def team():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        team_id = request.form.get("team") or ""
        ok, err = set_team(user, team_id)
        if not ok:
            flash(err, "error")
            return render_template(
                "team.html",
                user_email=user.email,
                team_labels=Config.TEAM_LABELS,
                is_admin=is_admin(user),
            )
        return redirect(url_for("generator.generator"))

    return render_template(
        "team.html",
        user_email=user.email,
        team_labels=Config.TEAM_LABELS,
        is_admin=is_admin(user),
    )


@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    logout_user_session()
    return redirect(url_for("auth.login"))
