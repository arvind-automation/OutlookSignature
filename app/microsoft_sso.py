from __future__ import annotations

import secrets
from typing import Any

import msal
import requests
from flask import current_app

GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"
GRAPH_ME_SELECT = (
    "givenName,surname,mail,userPrincipalName,jobTitle,mobilePhone,"
    "businessPhones,companyName,officeLocation,displayName"
)
GRAPH_MANAGER_SELECT = (
    "id,givenName,surname,mail,userPrincipalName"
)
GRAPH_USERS_URL = "https://graph.microsoft.com/v1.0/users"


def microsoft_sso_enabled() -> bool:
    return bool(current_app.config.get("MICROSOFT_SSO_ENABLED"))


def microsoft_redirect_uri() -> str:
    base = (current_app.config.get("APP_BASE_URL") or "").rstrip("/")
    return f"{base}/auth/microsoft/callback"


def _authority() -> str:
    tenant = current_app.config["AZURE_TENANT_ID"]
    return f"https://login.microsoftonline.com/{tenant}"


def build_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        current_app.config["AZURE_CLIENT_ID"],
        authority=_authority(),
        client_credential=current_app.config["AZURE_CLIENT_SECRET"],
    )


def build_auth_url(state: str) -> str:
    app = build_msal_app()
    return app.get_authorization_request_url(
        scopes=list(current_app.config["MICROSOFT_SSO_SCOPES"]),
        state=state,
        redirect_uri=microsoft_redirect_uri(),
        prompt="select_account",
    )


def exchange_code_for_token(code: str) -> dict[str, Any]:
    app = build_msal_app()
    return app.acquire_token_by_authorization_code(
        code,
        scopes=list(current_app.config["MICROSOFT_SSO_SCOPES"]),
        redirect_uri=microsoft_redirect_uri(),
    )


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def claims_email(claims: dict[str, Any] | None) -> str:
    claims = claims or {}
    for key in ("preferred_username", "email", "upn"):
        value = (claims.get(key) or "").strip()
        if value and "@" in value:
            return value.lower()
    return ""


def claims_names(claims: dict[str, Any] | None) -> tuple[str, str]:
    claims = claims or {}
    first = (claims.get("given_name") or "").strip()
    last = (claims.get("family_name") or "").strip()
    if first or last:
        return first, last
    name = (claims.get("name") or "").strip()
    if name:
        parts = name.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])
    return "", ""


def _graph_phone(person: dict[str, Any] | None) -> str:
    person = person or {}
    mobile = (person.get("mobilePhone") or "").strip()
    if mobile:
        return mobile
    phones = person.get("businessPhones") or []
    if isinstance(phones, list):
        for phone in phones:
            value = (phone or "").strip()
            if value:
                return value
    return ""


def _graph_names(person: dict[str, Any] | None) -> tuple[str, str]:
    person = person or {}
    first = (person.get("givenName") or "").strip()
    last = (person.get("surname") or "").strip()
    if first or last:
        return first, last
    display = (person.get("displayName") or "").strip()
    if display:
        parts = display.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])
    return "", ""


def _graph_email(person: dict[str, Any] | None) -> str:
    person = person or {}
    for key in ("mail", "userPrincipalName"):
        value = (person.get(key) or "").strip()
        if value and "@" in value:
            return value.lower()
    return ""


def _map_person_to_manager_fields(person: dict[str, Any] | None) -> dict[str, str]:
    first, last = _graph_names(person)
    return {
        "managerFirstName": first,
        "managerLastName": last,
        "managerEmail": _graph_email(person),
    }


def _map_person_to_manager2_fields(person: dict[str, Any] | None) -> dict[str, str]:
    first, last = _graph_names(person)
    return {
        "manager2FirstName": first,
        "manager2LastName": last,
        "manager2Email": _graph_email(person),
    }


def _same_graph_person(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    """True when two Graph user objects refer to the same person."""
    a = a or {}
    b = b or {}
    a_id = (a.get("id") or "").strip()
    b_id = (b.get("id") or "").strip()
    if a_id and b_id:
        return a_id == b_id
    a_email = _graph_email(a)
    b_email = _graph_email(b)
    return bool(a_email) and a_email == b_email


def _fetch_user_manager(
    headers: dict[str, str],
    user_id: str,
    *,
    log_label: str,
) -> dict[str, Any] | None:
    """Fetch a user's direct manager via GET /users/{id}/manager."""
    user_id = (user_id or "").strip()
    if not user_id:
        return None
    try:
        resp = requests.get(
            f"{GRAPH_USERS_URL}/{user_id}/manager",
            headers=headers,
            params={"$select": GRAPH_MANAGER_SELECT},
            timeout=10,
        )
        if resp.ok:
            return resp.json() or {}
        if resp.status_code not in (404, 403):
            current_app.logger.warning(
                "Graph %s failed status=%s body=%s",
                log_label,
                resp.status_code,
                resp.text[:300],
            )
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Graph %s request failed", log_label)
    return None


def fetch_graph_profile(access_token: str) -> dict[str, str]:
    """Fetch /me (+ optional L1/L2 managers) and map to generator form prefill keys."""
    if not access_token:
        return {}

    headers = {"Authorization": f"Bearer {access_token}"}
    me: dict[str, Any] = {}
    try:
        resp = requests.get(
            GRAPH_ME_URL,
            headers=headers,
            params={"$select": GRAPH_ME_SELECT},
            timeout=10,
        )
        if resp.ok:
            me = resp.json() or {}
        else:
            current_app.logger.warning(
                "Graph /me failed status=%s body=%s", resp.status_code, resp.text[:300]
            )
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Graph /me request failed")
        return {}

    first, last = _graph_names(me)
    prefill: dict[str, str] = {
        "firstName": first,
        "lastName": last,
        "email": _graph_email(me),
        "designation": (me.get("jobTitle") or "").strip(),
        "phone": _graph_phone(me),
        "organization": (me.get("companyName") or "").strip(),
        "address": (me.get("officeLocation") or "").strip(),
    }

    l1: dict[str, Any] | None = None
    try:
        mgr_resp = requests.get(
            f"{GRAPH_ME_URL}/manager",
            headers=headers,
            params={"$select": GRAPH_MANAGER_SELECT},
            timeout=10,
        )
        if mgr_resp.ok:
            l1 = mgr_resp.json() or {}
            prefill.update(_map_person_to_manager_fields(l1))
        elif mgr_resp.status_code not in (404, 403):
            current_app.logger.warning(
                "Graph /me/manager failed status=%s body=%s",
                mgr_resp.status_code,
                mgr_resp.text[:300],
            )
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Graph /me/manager request failed")

    l1_id = (l1.get("id") or "").strip() if l1 else ""
    if l1_id:
        l2 = _fetch_user_manager(
            headers,
            l1_id,
            log_label=f"/users/{l1_id}/manager",
        )
        if l2 and not _same_graph_person(l1, l2):
            prefill.update(_map_person_to_manager2_fields(l2))
        elif l2 and _same_graph_person(l1, l2):
            current_app.logger.info(
                "Graph L2 manager skipped: same person as L1 (id=%s)", l1_id
            )

    return {k: v for k, v in prefill.items() if v}
