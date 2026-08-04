from flask import Blueprint, redirect, render_template, session, url_for

from app.auth import current_user, is_admin
from app.config import Config
from app.models import Organization
from app.signatures import DEFAULT_FORM, TEMPLATES

generator_bp = Blueprint("generator", __name__)


@generator_bp.route("/generator")
def generator():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))

    team = session.get("team") or user.team
    if not team:
        return redirect(url_for("auth.team"))

    session["team"] = team
    orgs = Organization.query.order_by(Organization.id.asc()).all()
    team_label = Config.TEAM_LABELS.get(team, team)
    profile_prefill = session.get("profile_prefill") or {}

    return render_template(
        "generator.html",
        user_email=user.email,
        team=team,
        team_label=team_label,
        organizations=orgs,
        templates=TEMPLATES,
        defaults=DEFAULT_FORM,
        is_admin=is_admin(user),
        profile_prefill=profile_prefill,
    )
