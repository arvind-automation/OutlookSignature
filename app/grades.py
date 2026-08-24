"""Authoritative grade-to-signature-access policy."""

from __future__ import annotations

HIERARCHY_TEMPLATE = "hierarchy"
STANDARD_TEMPLATE = "standard"
TEAM_BY_TEMPLATE = {HIERARCHY_TEMPLATE: "sales", STANDARD_TEMPLATE: "gcc"}


def _entry(new_grade: str, template: str) -> dict[str, str]:
    return {"newGrade": new_grade, "template": template}


# The selected current grade is persisted; the new grade and permitted
# signature type are always derived from this single configuration.
GRADE_CONFIG = {
    "T1": _entry("4|A", HIERARCHY_TEMPLATE), "OT": _entry("4|A", HIERARCHY_TEMPLATE), "GET": _entry("4|A", HIERARCHY_TEMPLATE), "MT": _entry("4|A", HIERARCHY_TEMPLATE), "DET": _entry("4|A", HIERARCHY_TEMPLATE), "PGT": _entry("4|A", HIERARCHY_TEMPLATE), "E1": _entry("4|A", HIERARCHY_TEMPLATE),
    "E2": _entry("4|B", HIERARCHY_TEMPLATE), "E3": _entry("4|C", HIERARCHY_TEMPLATE), "MA": _entry("4|C", HIERARCHY_TEMPLATE), "M1": _entry("3|A", HIERARCHY_TEMPLATE),
    "M2": _entry("3|B", STANDARD_TEMPLATE), "M3": _entry("3|B", STANDARD_TEMPLATE), "M3H1": _entry("3|B", STANDARD_TEMPLATE), "GM-G1": _entry("3|B", STANDARD_TEMPLATE), "GM-G2": _entry("3|B", STANDARD_TEMPLATE), "BMH3": _entry("2|A", STANDARD_TEMPLATE), "BMH4": _entry("2|A", STANDARD_TEMPLATE), "SGM-G3": _entry("2|A", STANDARD_TEMPLATE), "CGM-G4": _entry("2|A", STANDARD_TEMPLATE), "BMH5": _entry("2|B", STANDARD_TEMPLATE), "AVP-V1": _entry("2|B", STANDARD_TEMPLATE), "JVP-V2": _entry("2|B", STANDARD_TEMPLATE), "BMH6": _entry("1|A", STANDARD_TEMPLATE), "BMH7": _entry("1|A", STANDARD_TEMPLATE), "BMH8": _entry("1|A", STANDARD_TEMPLATE),
    "4|A": _entry("4|A", HIERARCHY_TEMPLATE), "4|B": _entry("4|B", HIERARCHY_TEMPLATE), "4|C": _entry("4|C", HIERARCHY_TEMPLATE), "3|A": _entry("3|A", HIERARCHY_TEMPLATE),
    "3|B": _entry("3|B", STANDARD_TEMPLATE), "2|A": _entry("2|A", STANDARD_TEMPLATE), "2|B": _entry("2|B", STANDARD_TEMPLATE), "1|A": _entry("1|A", STANDARD_TEMPLATE),
}


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
