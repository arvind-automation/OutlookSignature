from flask import Blueprint, redirect, render_template, session, url_for

from app.auth import current_user, is_admin
from app.config import Config
from app.grades import get_allowed_team, get_new_grade
from app.models import Organization
from app.signatures import DEFAULT_FORM, TEMPLATES


LOCKED_ORGANIZATION_SLUG = "arvind-gcc"

generator_bp = Blueprint("generator", __name__)


@generator_bp.route("/generator")
def generator():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))

    team = get_allowed_team(user.grade)
    if not team:
        return redirect(url_for("auth.grade"))

    orgs = Organization.query.filter_by(slug=LOCKED_ORGANIZATION_SLUG).all()
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
        grade=user.grade,
        new_grade=get_new_grade(user.grade),
        user_name=" ".join(part for part in (user.first_name, user.last_name) if part) or user.email,
    )
