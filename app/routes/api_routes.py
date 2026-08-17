from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request, session

from app.auth import current_user, write_audit
from app.extensions import db
from app.models import Organization, SavedSignature
from app.signatures import DEFAULT_FORM, build_signature_html, assets_from_org

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _request_public_asset_origin(candidate: str = "") -> str:
    """Return a browser-supplied HTTPS origin only when it matches this host."""
    origin = (candidate or request.headers.get("Origin") or "").strip()
    parsed = urlparse(origin)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.netloc.casefold() != request.host.casefold()
    ):
        return ""
    return f"https://{parsed.netloc}"


def _require_api_user():
    user = current_user()
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return user, None


def _session_team(user) -> str:
    return (session.get("team") or getattr(user, "team", None) or "").strip().lower()


@api_bp.get("/organizations")
def list_organizations():
    user, err = _require_api_user()
    if err:
        return err
    orgs = Organization.query.order_by(Organization.id.asc()).all()
    return jsonify({"organizations": [o.to_dict() for o in orgs]})


@api_bp.post("/preview")
def preview():
    user, err = _require_api_user()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    form = payload.get("form") or {}
    template_id = (payload.get("templateId") or "standard").strip()
    if template_id not in current_app.config["ALLOWED_TEMPLATES"]:
        template_id = "standard"
    for_email = bool(payload.get("forEmail"))
    # Template hierarchy is determined by the authenticated session, never by
    # client state supplied with the preview request.
    team = _session_team(user)

    company = (form.get("company") or "").strip()
    org = Organization.query.filter_by(slug=company).first() if company else None

    if not org:
        return jsonify(
            {
                "html": (
                    '<p style="margin:0;padding:32px 16px;text-align:center;color:#666666;'
                    'font-family:Arial,Helvetica,sans-serif;">'
                    "Select an organization above to preview your signature.</p>"
                ),
                "needsOrganization": True,
            }
        )

    assets = assets_from_org(
        org,
        for_email=for_email,
        public_asset_base_url=(
            _request_public_asset_origin(payload.get("assetOrigin") or "")
            if for_email
            else ""
        ),
    )
    html = build_signature_html(template_id, form, assets, team=team)
    copy_error = ""
    if for_email and template_id != "minimal" and not assets.get("logo"):
        copy_error = (
            "Rich copy requires a public HTTPS asset origin. Ask an administrator "
            "to configure PUBLIC_ASSET_BASE_URL."
        )
    if (
        for_email
        and template_id == "standard"
        and org.banner_path
        and not assets.get("banner")
    ):
        copy_error = (
            "Rich copy requires a public HTTPS asset origin for the campaign banner. "
            "Ask an administrator to configure PUBLIC_ASSET_BASE_URL."
        )
    return jsonify(
        {
            "html": html,
            "needsOrganization": False,
            "copyReady": not bool(copy_error),
            "copyError": copy_error,
        }
    )


@api_bp.get("/signature")
def get_signature():
    user, err = _require_api_user()
    if err:
        return err

    saved = SavedSignature.query.filter_by(user_id=user.id).first()
    if not saved:
        defaults = dict(DEFAULT_FORM)
        defaults["email"] = user.email
        if user.first_name:
            defaults["firstName"] = user.first_name
        if user.last_name:
            defaults["lastName"] = user.last_name
        return jsonify({"form": defaults, "isDefault": True, "team": _session_team(user)})

    return jsonify(
        {"form": saved.to_form_dict(), "isDefault": False, "team": _session_team(user)}
    )


@api_bp.post("/signature")
def save_signature():
    user, err = _require_api_user()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    form = payload.get("form") or {}
    template_id = (payload.get("templateId") or form.get("templateId") or "standard").strip()
    if template_id not in current_app.config["ALLOWED_TEMPLATES"]:
        template_id = "standard"

    company = (form.get("company") or "").strip()
    org = Organization.query.filter_by(slug=company).first() if company else None

    saved = SavedSignature.query.filter_by(user_id=user.id).first()
    if saved is None:
        saved = SavedSignature(user_id=user.id)
        db.session.add(saved)

    saved.organization_id = org.id if org else None
    saved.template_id = template_id
    saved.first_name = (form.get("firstName") or "")[:120]
    saved.last_name = (form.get("lastName") or "")[:120]
    saved.email = (form.get("email") or user.email or "")[:255]
    saved.designation = (form.get("designation") or "")[:255]
    saved.phone = (form.get("phone") or "")[:64]
    # Organization identity and website are backend-controlled.
    saved.organization_name = (org.organization if org else "")[:255]
    saved.website = (org.website if org else "")[:255]
    saved.address = form.get("address") or ""
    saved.manager_first_name = (form.get("managerFirstName") or "")[:120]
    saved.manager_last_name = (form.get("managerLastName") or "")[:120]
    saved.manager_designation = (form.get("managerDesignation") or "")[:255]
    saved.manager_email = (form.get("managerEmail") or "")[:255]
    saved.manager_phone = (form.get("managerPhone") or "")[:64]
    saved.manager2_first_name = (form.get("manager2FirstName") or "")[:120]
    saved.manager2_last_name = (form.get("manager2LastName") or "")[:120]
    saved.manager2_designation = (form.get("manager2Designation") or "")[:255]
    saved.manager2_email = (form.get("manager2Email") or "")[:255]
    saved.manager2_phone = (form.get("manager2Phone") or "")[:64]

    db.session.commit()
    write_audit(
        "signature_saved",
        user_id=user.id,
        details={
            "templateId": template_id,
            "company": company,
            "team": _session_team(user),
        },
    )
    return jsonify({"ok": True, "form": saved.to_form_dict()})


@api_bp.post("/audit")
def client_audit():
    user, err = _require_api_user()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    action = (payload.get("action") or "").strip()
    allowed = {"signature_copied", "html_copied"}
    if action not in allowed:
        return jsonify({"error": "Invalid action"}), 400

    write_audit(action, user_id=user.id, details=payload.get("details") or {})
    return jsonify({"ok": True})
