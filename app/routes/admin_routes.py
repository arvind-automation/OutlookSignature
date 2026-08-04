from __future__ import annotations

import re
from datetime import datetime, timezone

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.auth import current_user, is_admin
from app.config import Config
from app.models import AuditLog, User

admin_bp = Blueprint("admin", __name__)

PAGE_SIZE = 50

ACTION_LABELS = {
    "login_success": "Signed in",
    "login_failed": "Login failed",
    "team_selected": "Team selected",
    "signature_saved": "Signature saved",
    "signature_copied": "Signature copied",
    "html_copied": "HTML copied",
    "logout": "Signed out",
    "db_initialized": "Database initialized",
}

LOGIN_FAIL_REASONS = {
    "bad_password": "wrong password",
    "invalid_domain": "email domain not allowed",
}

TEMPLATE_LABELS = {
    "standard": "Standard",
    "compact": "Compact",
    "minimal": "Minimal",
}

KEY_LABELS = {
    "email": "Email",
    "reason": "Reason",
    "team": "Team",
    "templateId": "Template",
    "company": "Org",
    "organization": "Org",
}


def friendly_action_label(action: str) -> str:
    if action in ACTION_LABELS:
        return ACTION_LABELS[action]
    return action.replace("_", " ").strip().capitalize() or "—"


def _team_label(team: str | None) -> str:
    if not team:
        return ""
    return Config.TEAM_LABELS.get(team, str(team))


def _humanize_key(key: str) -> str:
    if key in KEY_LABELS:
        return KEY_LABELS[key]
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key.replace("_", " "))
    return spaced.strip().capitalize() or key


def _format_value(key: str, value) -> str:
    if value is None or value == "":
        return ""
    if key == "team":
        return _team_label(str(value))
    if key == "templateId":
        return TEMPLATE_LABELS.get(str(value), str(value).capitalize())
    if key == "reason":
        return LOGIN_FAIL_REASONS.get(str(value), str(value).replace("_", " "))
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def _fallback_details(details: dict) -> str:
    parts = []
    for key, value in details.items():
        formatted = _format_value(key, value)
        if formatted:
            parts.append(f"{_humanize_key(key)}: {formatted}")
    return " · ".join(parts) if parts else "—"


def format_audit_details(action: str, details) -> str:
    if not isinstance(details, dict):
        if details in (None, "", {}):
            details = {}
        else:
            return str(details)

    if action == "login_success":
        return "Signed in successfully"

    if action == "login_failed":
        reason = LOGIN_FAIL_REASONS.get(
            str(details.get("reason") or ""),
            (str(details.get("reason")).replace("_", " ") if details.get("reason") else ""),
        )
        if reason:
            return f"Login failed — {reason}"
        return "Login failed"

    if action == "team_selected":
        label = _team_label(details.get("team"))
        return f"Selected team: {label}" if label else "Selected a team"

    if action == "signature_saved":
        bits = []
        template = _format_value("templateId", details.get("templateId"))
        company = details.get("company")
        team = _team_label(details.get("team"))
        if template:
            bits.append(f"Template: {template}")
        if company:
            bits.append(f"Org: {company}")
        if team:
            bits.append(f"Team: {team}")
        if bits:
            return "Saved signature — " + " · ".join(bits)
        return "Saved signature"

    if action == "signature_copied":
        return "Copied signature to clipboard"

    if action == "html_copied":
        return "Copied HTML to clipboard"

    if action == "logout":
        return "Signed out"

    if action == "db_initialized":
        return "Database initialized"

    if not details:
        return "—"

    return _fallback_details(details)


@admin_bp.route("/admin")
def overview():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not is_admin(user):
        abort(403)

    page = request.args.get("page", 1, type=int) or 1
    if page < 1:
        page = 1

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_logs = AuditLog.query.count()
    logins_today = AuditLog.query.filter(
        AuditLog.action == "login_success",
        AuditLog.created_at >= today_start,
    ).count()
    signatures_saved = AuditLog.query.filter_by(action="signature_saved").count()
    signatures_copied = AuditLog.query.filter(
        AuditLog.action.in_(("signature_copied", "html_copied"))
    ).count()

    pagination = (
        AuditLog.query.outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .paginate(page=page, per_page=PAGE_SIZE, error_out=False)
    )

    rows = []
    for entry in pagination.items:
        email = entry.user.email if entry.user else "—"
        details = entry.details or {}
        rows.append(
            {
                "created_at": entry.created_at,
                "email": email,
                "action": friendly_action_label(entry.action),
                "ip_address": entry.ip_address or "—",
                "details": format_audit_details(entry.action, details),
            }
        )

    return render_template(
        "admin.html",
        user_email=user.email,
        rows=rows,
        pagination=pagination,
        summary={
            "total_logs": total_logs,
            "logins_today": logins_today,
            "signatures_saved": signatures_saved,
            "signatures_copied": signatures_copied,
        },
    )
