"""Authoritative grade-to-signature-access policy and reference data."""

from __future__ import annotations

HIERARCHY_TEMPLATE = "hierarchy"
STANDARD_TEMPLATE = "standard"
TEAM_BY_TEMPLATE = {HIERARCHY_TEMPLATE: "sales", STANDARD_TEMPLATE: "gcc"}

# This single table drives authorization, the help modal, and the picker.
GRADE_REFERENCE_ROWS = (
    (("T1", "OT", "GET", "MT", "DET", "PGT"), "4|A", HIERARCHY_TEMPLATE, "Trainees"),
    (("E1",), "4|A", HIERARCHY_TEMPLATE, "Executives"),
    (("E2",), "4|B", HIERARCHY_TEMPLATE, "Senior Executive / Associate Manager"),
    (("E3", "MA"), "4|C", HIERARCHY_TEMPLATE, "Assistant Manager"),
    (("M1",), "3|A", HIERARCHY_TEMPLATE, "Manager"),
    (("M2", "M3", "M3H1", "GM-G1", "GM-G2"), "3|B", STANDARD_TEMPLATE, "Sr. Manager / Chief Manager / Dy. GM"),
    (("BMH3", "BMH4", "SGM-G3", "CGM-G4"), "2|A", STANDARD_TEMPLATE, "General Manager / Associate VP"),
    (("BMH5", "AVP-V1", "JVP-V2"), "2|B", STANDARD_TEMPLATE, "Vice President"),
    (("BMH6", "BMH7", "BMH8"), "1|A", STANDARD_TEMPLATE, "CEO / CXO / CBO / COO"),
)


def _build_grade_config() -> dict[str, dict[str, str]]:
    config: dict[str, dict[str, str]] = {}
    for legacy_grades, new_grade, template, _designation in GRADE_REFERENCE_ROWS:
        for grade in legacy_grades:
            config[grade] = {"newGrade": new_grade, "template": template}
        config[new_grade] = {"newGrade": new_grade, "template": template}
    return config


GRADE_CONFIG = _build_grade_config()


def get_grade_config(grade: str | None) -> dict[str, str] | None:
    return GRADE_CONFIG.get((grade or "").strip().upper())


def get_allowed_team(grade: str | None) -> str | None:
    config = get_grade_config(grade)
    return TEAM_BY_TEMPLATE.get(config["template"]) if config else None


def get_allowed_template(grade: str | None) -> str | None:
    config = get_grade_config(grade)
    return config["template"] if config else None


def get_new_grade(grade: str | None) -> str | None:
    config = get_grade_config(grade)
    return config["newGrade"] if config else None


def get_all_grades() -> tuple[str, ...]:
    return tuple(GRADE_CONFIG)


def get_selectable_grade_options() -> tuple[dict[str, str], ...]:
    """Return each new grade once, with its complete designation label."""
    grouped: dict[str, list[str]] = {}
    for _legacy, new_grade, _template, designation in GRADE_REFERENCE_ROWS:
        grouped.setdefault(new_grade, []).append(designation)
    return tuple(
        {"code": grade, "designation": " / ".join(designations)}
        for grade, designations in grouped.items()
    )


def get_grade_reference_rows() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "currentGrades": ", ".join(legacy_grades),
            "newGrade": new_grade,
            "template": "Hierarchy Template Only" if template == HIERARCHY_TEMPLATE else "Standard Template Only",
            "designation": designation,
        }
        for legacy_grades, new_grade, template, designation in GRADE_REFERENCE_ROWS
    )
