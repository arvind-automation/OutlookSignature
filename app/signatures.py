"""Signature HTML builders — ported from src/app.js with identical structure."""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

from flask import current_app, url_for

BRAND = {
    "maroon": "#8B1538",
    "charcoal": "#2C2C2C",
    "muted": "#6B6B6B",
    "text": "#6B6B6B",
    "link": "#8B1538",
}

TEMPLATES = [
    {
        "id": "standard",
        "name": "Standard",
        "description": "Contact details and logo; 95 Years banner for Arvind Limited only",
    },
    {
        "id": "compact",
        "name": "Compact",
        "description": "Contact details and logo without banner",
    },
    {
        "id": "minimal",
        "name": "Minimal",
        "description": "Text-only signature for lightweight clients",
    },
]

DEFAULT_FORM = {
    "company": "arvind-limited",
    "firstName": "FirstName",
    "lastName": "LastName",
    "email": "name@arvind.in",
    "designation": "Designation",
    "phone": "+91 XXXXX XXXXX",
    "organization": "Arvind Limited",
    "website": "www.arvind.com",
    "address": "",
    "managerFirstName": "",
    "managerLastName": "",
    "managerDesignation": "",
    "managerEmail": "",
    "managerPhone": "",
    "manager2FirstName": "",
    "manager2LastName": "",
    "manager2Designation": "",
    "manager2Email": "",
    "manager2Phone": "",
}

# Canonical org seed data matching app.js ORGANIZATIONS (paths relative to static/)
ORGANIZATION_SEEDS = [
    {
        "slug": "anup-engineering",
        "label": "The Anup Engineering Limited",
        "organization": "The Anup Engineering Limited",
        "website": "www.anupengineering.com",
        "logo_path": "assets/anup-engineering-logo.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.svg",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-smartspaces",
        "label": "Arvind SmartSpaces",
        "organization": "Arvind SmartSpaces",
        "website": "www.arvindsmartspaces.com",
        "logo_path": "assets/arvind-smartspaces-logo.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.svg",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-fashions",
        "label": "Arvind Fashions Limited",
        "organization": "Arvind Fashions Limited",
        "website": "www.arvindfashions.com",
        "logo_path": "assets/arvind-fashions-logo.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.svg",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-limited",
        "label": "Arvind Limited",
        "organization": "Arvind Limited",
        "website": "www.arvind.com",
        "logo_path": "assets/arvind-company-logo.png",
        "banner_path": "assets/arvind-95-banner.png",
        "watermark_path": "assets/watermark-a.svg",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-gcc",
        "label": "Arvind GCC",
        "organization": "Arvind GCC",
        "website": "www.arvind.com",
        "logo_path": "assets/arvind-gcc-logo.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.svg",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
]

ASSET_FALLBACKS = {
    "assets/anup-engineering-logo.png": "assets/arvind-logo-white.svg",
    "assets/arvind-smartspaces-logo.png": "assets/arvind-logo-white.svg",
    "assets/arvind-fashions-logo.png": "assets/arvind-logo-white.svg",
    "assets/arvind-company-logo.png": "assets/arvind-logo-white.svg",
    "assets/arvind-gcc-logo.png": "assets/arvind-logo-white.svg",
    "assets/arvind-95-banner.png": "assets/arvind-95-banner.svg",
}


def escape_html(value) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def normalize_form_values(raw: dict) -> dict:
    first_name = (raw.get("firstName") or "").strip()
    last_name = (raw.get("lastName") or "").strip()
    full_name = " ".join([p for p in (first_name, last_name) if p]) or "Your Name"
    designation = (raw.get("designation") or "").strip() or "Your Designation"
    phone = (raw.get("phone") or "").strip() or "+91 XXXXX XXXXX"
    email = (raw.get("email") or "").strip() or "name@arvind.in"
    organization = (raw.get("organization") or "").strip() or "Arvind Limited"
    address = (raw.get("address") or "").strip()
    website_input = "www.arvind.com"
    website_href = "https://www.arvind.com"

    mgr_first = (raw.get("managerFirstName") or "").strip()
    mgr_last = (raw.get("managerLastName") or "").strip()
    manager_full_name = " ".join([p for p in (mgr_first, mgr_last) if p])
    manager_designation = (raw.get("managerDesignation") or "").strip()
    manager_email = (raw.get("managerEmail") or "").strip()
    manager_phone = (raw.get("managerPhone") or "").strip()

    mgr2_first = (raw.get("manager2FirstName") or "").strip()
    mgr2_last = (raw.get("manager2LastName") or "").strip()
    manager2_full_name = " ".join([p for p in (mgr2_first, mgr2_last) if p])
    manager2_designation = (raw.get("manager2Designation") or "").strip()
    manager2_email = (raw.get("manager2Email") or "").strip()
    manager2_phone = (raw.get("manager2Phone") or "").strip()

    return {
        "fullName": full_name,
        "designation": designation,
        "phone": phone,
        "email": email,
        "organization": organization,
        "address": address,
        "websiteLabel": re.sub(r"^https?://", "", website_input, flags=re.I),
        "websiteHref": website_href,
        "managerFullName": manager_full_name,
        "managerDesignation": manager_designation,
        "managerEmail": manager_email,
        "managerPhone": manager_phone,
        "hasManager": bool(
            manager_full_name or manager_designation or manager_email or manager_phone
        ),
        "manager2FullName": manager2_full_name,
        "manager2Designation": manager2_designation,
        "manager2Email": manager2_email,
        "manager2Phone": manager2_phone,
        "hasManager2": bool(
            manager2_full_name or manager2_designation or manager2_email or manager2_phone
        ),
    }


def contact_block(values: dict, *, show_salutation: bool = False, compact: bool = False) -> str:
    name_size = "15px" if compact else "16px"
    title_size = "11px" if compact else "12px"
    html = ""
    if show_salutation:
        html += (
            f'<p style="margin:0 0 8px;font-size:11px;line-height:1.4;color:{BRAND["muted"]};">'
            "With Regards,</p>"
        )
    html += (
        f'<p style="margin:0 0 4px;font-size:{name_size};line-height:1.3;font-weight:700;'
        f'color:{BRAND["charcoal"]};">{escape_html(values["fullName"])}</p>'
    )
    html += (
        f'<p style="margin:0 0 10px;font-size:{title_size};line-height:1.4;'
        f'color:{BRAND["muted"]};">{escape_html(values["designation"])}</p>'
    )
    html += (
        f'<p style="margin:0 0 2px;font-size:11px;line-height:1.5;color:{BRAND["muted"]};">'
        f'{escape_html(values["phone"])}</p>'
    )
    html += (
        f'<p style="margin:0 0 2px;font-size:11px;line-height:1.5;color:{BRAND["muted"]};">'
        f'<a href="mailto:{escape_html(values["email"])}" '
        f'style="color:{BRAND["link"]};text-decoration:none;">'
        f'{escape_html(values["email"])}</a></p>'
    )
    html += (
        f'<p style="margin:0 0 2px;font-size:10px;line-height:1.5;">'
        f'<a href="{escape_html(values["websiteHref"])}" '
        f'style="color:{BRAND["link"]};text-decoration:none;">'
        f'{escape_html(values["websiteLabel"])}</a></p>'
    )
    if values["address"]:
        html += (
            f'<p style="margin:4px 0 0;font-size:10px;line-height:1.5;color:{BRAND["muted"]};">'
            f'{escape_html(values["address"])}</p>'
        )
    return html


def _one_manager_block(
    *,
    heading: str,
    full_name: str,
    designation: str,
    phone: str,
    email: str,
    compact: bool,
    heading_margin_top: str = "12px",
) -> str:
    title_size = "10px" if compact else "11px"
    name_size = "12px" if compact else "13px"
    html = (
        f'<p style="margin:{heading_margin_top} 0 4px;font-size:{title_size};line-height:1.4;'
        f'color:{BRAND["muted"]};font-weight:600;">{escape_html(heading)}</p>'
    )
    if full_name:
        html += (
            f'<p style="margin:0 0 2px;font-size:{name_size};line-height:1.3;font-weight:700;'
            f'color:{BRAND["charcoal"]};">{escape_html(full_name)}</p>'
        )
    if designation:
        html += (
            f'<p style="margin:0 0 6px;font-size:10px;line-height:1.4;'
            f'color:{BRAND["muted"]};">{escape_html(designation)}</p>'
        )
    if phone:
        html += (
            f'<p style="margin:0 0 2px;font-size:10px;line-height:1.5;color:{BRAND["muted"]};">'
            f"{escape_html(phone)}</p>"
        )
    if email:
        html += (
            f'<p style="margin:0 0 2px;font-size:10px;line-height:1.5;color:{BRAND["muted"]};">'
            f'<a href="mailto:{escape_html(email)}" '
            f'style="color:{BRAND["link"]};text-decoration:none;">'
            f"{escape_html(email)}</a></p>"
        )
    return html


def manager_block(values: dict, *, compact: bool = False) -> str:
    has_l1 = bool(values.get("hasManager"))
    has_l2 = bool(values.get("hasManager2"))
    if not has_l1 and not has_l2:
        return ""

    l1 = (
        _one_manager_block(
            heading="Reporting to",
            full_name=values.get("managerFullName") or "",
            designation=values.get("managerDesignation") or "",
            phone=values.get("managerPhone") or "",
            email=values.get("managerEmail") or "",
            compact=compact,
            heading_margin_top="0",
        )
        if has_l1
        else ""
    )
    l2 = (
        _one_manager_block(
            heading="Level 2 Manager",
            full_name=values.get("manager2FullName") or "",
            designation=values.get("manager2Designation") or "",
            phone=values.get("manager2Phone") or "",
            email=values.get("manager2Email") or "",
            compact=compact,
            heading_margin_top="0",
        )
        if has_l2
        else ""
    )

    if has_l1 and has_l2:
        return (
            '<table cellpadding="0" cellspacing="0" border="0" '
            'style="width:100%;border-collapse:collapse;margin-top:12px;">'
            "<tr>"
            f'<td style="width:50%;vertical-align:top;padding:0 8px 0 0;">{l1}</td>'
            f'<td style="width:50%;vertical-align:top;padding:0 0 0 8px;">{l2}</td>'
            "</tr></table>"
        )

    # Single manager: restore top spacing above the heading
    single = l1 or l2
    return f'<div style="margin-top:12px;">{single}</div>'


def body_content(values: dict, *, show_salutation: bool = False, compact: bool = False, team: str = "") -> str:
    html = contact_block(values, show_salutation=show_salutation, compact=compact)
    if (team or "").lower() == "sales":
        html += manager_block(values, compact=compact)
    return html


def logo_cell(assets: dict, width: str = "270px") -> str:
    logo_width = assets.get("logoWidth") or 230
    alt = assets.get("logoAlt") or "Company logo"
    return (
        f'<td style="width:{width};vertical-align:middle;padding:18px 16px;'
        f'border-left:2px solid {BRAND["maroon"]};text-align:center;">'
        f'<img src="{assets["logo"]}" alt="{escape_html(alt)}" width="{logo_width}" '
        f'style="display:block;margin:0 auto;border:0;outline:none;text-decoration:none;'
        f'max-width:100%;height:auto;" /></td>'
    )


def banner_row(banner_url: str) -> str:
    return (
        '<tr><td colspan="2" style="padding:0;line-height:0;font-size:0;">'
        f'<img src="{banner_url}" alt="95 Years of Legacy" width="600" height="110" '
        'style="display:block;width:600px;max-width:600px;height:auto;border:0;'
        'outline:none;text-decoration:none;" /></td></tr>'
    )


def build_standard_template(values: dict, assets: dict, *, team: str = "") -> str:
    html = (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="width:600px;max-width:600px;border-collapse:collapse;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        "<tr>"
        f'<td style="width:330px;vertical-align:top;padding:18px 16px 14px 18px;'
        f'background-color:#ffffff;background-image:url({assets["watermark"]});'
        "background-repeat:no-repeat;background-position:right 8px top 8px;"
        'background-size:150px auto;">'
        f"{body_content(values, team=team)}"
        "</td>"
        f"{logo_cell(assets)}"
        "</tr>"
    )
    if assets.get("banner"):
        html += banner_row(assets["banner"])
    html += "</table>"
    return html


def build_compact_template(values: dict, assets: dict, *, team: str = "") -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="width:560px;max-width:560px;border-collapse:collapse;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        "<tr>"
        f'<td style="width:320px;vertical-align:top;padding:16px 14px;'
        f'background-color:#ffffff;background-image:url({assets["watermark"]});'
        "background-repeat:no-repeat;background-position:right 6px top 6px;"
        'background-size:130px auto;">'
        f"{body_content(values, compact=True, team=team)}"
        "</td>"
        f'{logo_cell(assets, "240px")}'
        "</tr></table>"
    )


def build_minimal_template(values: dict, *, team: str = "") -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="width:420px;max-width:420px;border-collapse:collapse;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        '<tr><td style="padding:8px 0;">'
        f"{body_content(values, show_salutation=False, compact=True, team=team)}"
        f'<p style="margin:8px 0 0;font-size:10px;line-height:1.4;'
        f'color:{BRAND["muted"]};font-weight:700;">'
        f'{escape_html(values["organization"])}</p>'
        "</td></tr></table>"
    )


def build_signature_html(
    template_id: str, raw_values: dict, asset_urls: dict, *, team: str = ""
) -> str:
    values = normalize_form_values(raw_values)
    assets = {
        "logo": asset_urls["logo"],
        "banner": asset_urls.get("banner"),
        "watermark": asset_urls["watermark"],
        "logoBg": asset_urls.get("logoBg"),
        "logoWidth": asset_urls.get("logoWidth"),
        "logoAlt": asset_urls.get("logoAlt"),
    }
    if template_id == "compact":
        return build_compact_template(values, assets, team=team)
    if template_id == "minimal":
        return build_minimal_template(values, team=team)
    return build_standard_template(values, assets, team=team)


def static_root() -> Path:
    return Path(current_app.static_folder)


def resolve_static_path(rel_path: str | None) -> Path | None:
    if not rel_path:
        return None
    rel = rel_path.replace("\\", "/").lstrip("/")
    if rel.startswith("./"):
        rel = rel[2:]
    candidate = static_root() / rel
    if candidate.is_file():
        return candidate
    fallback = ASSET_FALLBACKS.get(rel)
    if fallback:
        fb = static_root() / fallback
        if fb.is_file():
            return fb
    return candidate if candidate.exists() else None


def public_asset_url(rel_path: str | None) -> str | None:
    if not rel_path:
        return None
    rel = rel_path.replace("\\", "/").lstrip("/")
    if rel.startswith("./"):
        rel = rel[2:]
    resolved = resolve_static_path(rel)
    if resolved and resolved.is_file():
        # Prefer actual file used (may be fallback)
        try:
            rel_used = str(resolved.relative_to(static_root())).replace("\\", "/")
        except ValueError:
            rel_used = rel
        return url_for("static", filename=rel_used)
    return url_for("static", filename=rel)


def file_to_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "application/octet-stream"
        if path.suffix.lower() == ".svg":
            mime = "image/svg+xml"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def assets_from_org(org, *, for_email: bool = False) -> dict:
    """Build asset URL dict from Organization model or dict-like."""
    if org is None:
        logo = "assets/arvind-company-logo.png"
        watermark = "assets/watermark-a.svg"
        banner = None
        logo_bg = BRAND["maroon"]
        logo_width = 230
        logo_alt = "Company logo"
    else:
        logo = getattr(org, "logo_path", None) or org.get("logo_path")
        watermark = getattr(org, "watermark_path", None) or org.get("watermark_path")
        banner = getattr(org, "banner_path", None)
        if banner is None and isinstance(org, dict):
            banner = org.get("banner_path")
        logo_bg = getattr(org, "logo_bg", None) or (
            org.get("logo_bg") if isinstance(org, dict) else "#ffffff"
        )
        logo_width = getattr(org, "logo_width", None) or (
            org.get("logo_width") if isinstance(org, dict) else 230
        )
        logo_alt = getattr(org, "label", None) or (
            org.get("label") if isinstance(org, dict) else "Company logo"
        )

    if for_email:
        logo_path = resolve_static_path(logo)
        watermark_path = resolve_static_path(watermark)
        banner_path = resolve_static_path(banner) if banner else None
        return {
            "logo": file_to_data_uri(logo_path) if logo_path and logo_path.is_file() else "",
            "watermark": (
                file_to_data_uri(watermark_path)
                if watermark_path and watermark_path.is_file()
                else ""
            ),
            "banner": (
                file_to_data_uri(banner_path)
                if banner_path and banner_path.is_file()
                else None
            ),
            "logoBg": logo_bg,
            "logoWidth": logo_width,
            "logoAlt": logo_alt,
        }

    return {
        "logo": public_asset_url(logo),
        "watermark": public_asset_url(watermark),
        "banner": public_asset_url(banner) if banner else None,
        "logoBg": logo_bg,
        "logoWidth": logo_width,
        "logoAlt": logo_alt,
    }
