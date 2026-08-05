from __future__ import annotations

import secrets

from flask import current_app, request, session

from app.extensions import db
from app.models import AuditLog, User

DEMO_PROFILES = {
    "nazeer.ahmed@arvind.in": {
        "first_name": "Nazeer",
        "last_name": "Ahmed",
    },
}


def is_admin(user: User | None) -> bool:
    if not user:
        return False
    return bool(getattr(user, "is_admin", False))


def is_allowed_email(email: str) -> bool:
    email = (email or "").lower().strip()
    return any(email.endswith(suffix) for suffix in current_app.config["ALLOWED_EMAIL_SUFFIXES"])


def names_from_email(email: str) -> tuple[str, str]:
    local = (email.split("@")[0] if email else "") or ""
    parts = [p for p in local.split(".") if p]
    first = parts[0].capitalize() if parts else ""
    last = parts[1].capitalize() if len(parts) > 1 else ""
    return first, last


def write_audit(action: str, user_id=None, details=None) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    )
    db.session.add(entry)
    db.session.commit()


def get_or_create_sso_user(
    email: str,
    first_name: str = "",
    last_name: str = "",
) -> tuple[User | None, str]:
    """Provision or load a user after a successful Microsoft SSO login."""
    email = (email or "").strip().lower()
    if not email:
        write_audit("login_failed", details={"reason": "sso_missing_email", "method": "microsoft"})
        return None, "Microsoft did not return an email address for this account."

    if not is_allowed_email(email):
        write_audit(
            "login_failed",
            details={"email": email, "reason": "invalid_domain", "method": "microsoft"},
        )
        return None, "Use your Arvind Microsoft account (for example, name@arvind.in)."

    user = User.query.filter_by(email=email).first()
    if user is None:
        profile = DEMO_PROFILES.get(email, {})
        derived_first, derived_last = names_from_email(email)
        user = User(
            email=email,
            first_name=(first_name or profile.get("first_name") or derived_first or None),
            last_name=(last_name or profile.get("last_name") or derived_last or None),
        )
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.commit()
    else:
        updated = False
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if updated:
            db.session.commit()

    write_audit(
        "login_success",
        user_id=user.id,
        details={"email": email, "method": "microsoft"},
    )
    return user, ""


def login_user_session(user: User) -> None:
    session.clear()
    session["user_id"] = user.id
    session["user_email"] = user.email
    # Team must be chosen explicitly after each login.
    session["team"] = ""
    session.permanent = True


def logout_user_session() -> None:
    user_id = session.get("user_id")
    if user_id:
        write_audit("logout", user_id=user_id)
    session.clear()


def current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def require_user():
    return current_user()


def set_team(user: User, team: str) -> tuple[bool, str]:
    team = (team or "").strip().lower()
    if team not in current_app.config["ALLOWED_TEAMS"]:
        return False, "Invalid team selection."
    user.team = team
    db.session.commit()
    session["team"] = team
    write_audit("team_selected", user_id=user.id, details={"team": team})
    return True, ""
