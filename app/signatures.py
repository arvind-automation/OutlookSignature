"""Outlook-safe HTML builders for Arvind email signatures."""

from __future__ import annotations

import re
import struct
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

from flask import current_app, url_for

BRAND = {
    "maroon": "#8B1538",
    "charcoal": "#2C2C2C",
    "muted": "#6B6B6B",
    "text": "#6B6B6B",
    "link": "#8B1538",
    "line": "#D8B7C2",
}

TEMPLATES = [
    {
        "id": "standard",
        "name": "Standard",
        "description": "Details, logo, social links and approved campaign banner",
    },
    {
        "id": "compact",
        "name": "Compact",
        "description": "Details, logo and social links without a banner",
    },
    {
        "id": "minimal",
        "name": "Minimal",
        "description": "Text-only signature for lightweight clients",
    },
    {
        "id": "logo-header",
        "name": "Logo Header",
        "description": "Prominent company logo with compact contact details",
    },
    {
        "id": "logo-sidebar",
        "name": "Logo Sidebar",
        "description": "Profile heading with logo, contacts and social links",
    },
    {
        "id": "logo-profile",
        "name": "Logo Profile",
        "description": "Circular company mark with a strong address footer",
    },
]

DEFAULT_FORM = {
    "company": "arvind-limited",
    "firstName": "",
    "lastName": "",
    "email": "",
    "designation": "",
    "phone": "",
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

# Canonical organization assets. Paths are always backend-controlled and are
# relative to app/static.
ORGANIZATION_SEEDS = [
    {
        "slug": "anup-engineering",
        "label": "The Anup Engineering Limited",
        "organization": "The Anup Engineering Limited",
        "website": "www.anupengineering.com",
        "logo_path": "assets/anup-engineering-logo-transparent.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.png",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-smartspaces",
        "label": "Arvind SmartSpaces",
        "organization": "Arvind SmartSpaces",
        "website": "www.arvindsmartspaces.com",
        "logo_path": "assets/arvind-smartspaces-logo-transparent.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.png",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-fashions",
        "label": "Arvind Fashions Limited",
        "organization": "Arvind Fashions Limited",
        "website": "www.arvindfashions.com",
        "logo_path": "assets/arvind-fashions-logo-transparent.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.png",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-limited",
        "label": "Arvind Limited",
        "organization": "Arvind Limited",
        "website": "www.arvind.com",
        "logo_path": "assets/arvind-company-logo-transparent.png",
        "banner_path": "assets/arvind-95-banner.png",
        "watermark_path": "assets/watermark-a.png",
        "logo_bg": "#ffffff",
        "logo_width": 230,
    },
    {
        "slug": "arvind-gcc",
        "label": "Arvind GCC",
        "organization": "Arvind GCC",
        "website": "www.arvind.com",
        "logo_path": "assets/arvind-gcc-logo-transparent.png",
        "banner_path": None,
        "watermark_path": "assets/watermark-a.png",
        "logo_bg": "#ffffff",
        "logo_width": 260,
    },
]

ASSET_FALLBACKS = {
    "assets/anup-engineering-logo-transparent.png": "assets/anup-engineering-logo.png",
    "assets/arvind-smartspaces-logo-transparent.png": "assets/arvind-smartspaces-logo.png",
    "assets/arvind-fashions-logo-transparent.png": "assets/arvind-fashions-logo.png",
    "assets/arvind-company-logo-transparent.png": "assets/arvind-company-logo.png",
    "assets/arvind-gcc-logo.png": "assets/arvind-logo-white.svg",
    "assets/arvind-gcc-logo-transparent.png": "assets/arvind-gcc-logo.png",
    "assets/arvind-95-banner.png": "assets/arvind-95-banner.svg",
}

# Profile destinations are approved backend configuration. Only verified
# LinkedIn profiles are enabled today; the remaining supported platforms stay
# hidden until official URLs are supplied.
ORGANIZATION_SOCIAL_LINKS = {
    "anup-engineering": {
        "linkedin": "https://www.linkedin.com/company/the-anup-engineering-limited",
        "instagram": (
            "https://www.instagram.com/explore/locations/135173883310729/"
            "anup-engineering-ltd/"
        ),
    },
    "arvind-smartspaces": {
        "linkedin": "https://www.linkedin.com/company/arvind-smartspaces",
        "instagram": "https://www.instagram.com/arvindsmartspaces/",
    },
    "arvind-fashions": {
        "linkedin": "https://www.linkedin.com/company/arvindfashions",
        "instagram": "https://www.instagram.com/arvindfashionslimited/",
    },
    "arvind-limited": {
        "linkedin": "https://www.linkedin.com/company/arvindlimited",
        "instagram": "https://www.instagram.com/arvind_limited/",
    },
    "arvind-gcc": {
        "linkedin": "https://www.linkedin.com/company/arvindlimited",
        "instagram": "https://www.instagram.com/arvind_limited/",
    },
}

SOCIAL_PLATFORM_CONFIG = {
    "facebook": {
        "label": "Facebook",
        "icon": "https://img.icons8.com/ios-filled/48/8b1538/facebook-new.png",
    },
    "x": {
        "label": "X",
        "icon": "https://img.icons8.com/ios-filled/48/8b1538/twitterx.png",
    },
    "linkedin": {
        "label": "LinkedIn",
        "icon": "https://img.icons8.com/color/48/linkedin.png",
    },
    "youtube": {
        "label": "YouTube",
        "icon": "https://img.icons8.com/ios-filled/48/8b1538/youtube-play.png",
    },
    "instagram": {
        "label": "Instagram",
        "icon": "https://img.icons8.com/fluency/48/instagram-new.png",
    },
}

ORGANIZATION_BANNER_LINKS = {
    "arvind-limited": "https://www.arvind.com",
}

_PLACEHOLDER_VALUES = {
    "null",
    "undefined",
    "firstname",
    "lastname",
    "your name",
    "your designation",
    "designation",
    "name@arvind.in",
    "+91 xxxxx xxxxx",
}
_EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
_EXTENSION_RE = re.compile(r"(?:\bext\.?|\bx|#)\s*\d+\s*$", re.I)


def escape_html(value) -> str:
    return escape(str(value), quote=True)


def clean_text(value) -> str:
    text = str(value or "").strip()
    if text.casefold() in _PLACEHOLDER_VALUES:
        return ""
    return text


def safe_email(value) -> str:
    email = clean_text(value)
    return email if email and _EMAIL_RE.fullmatch(email) else ""


def normalize_tel(value) -> str:
    visible = clean_text(value)
    if not visible or _EXTENSION_RE.search(visible):
        return ""
    if "+" in visible and not visible.lstrip().startswith("+"):
        return ""
    normalized = ("+" if visible.startswith("+") else "") + re.sub(r"\D", "", visible)
    digits = normalized.lstrip("+")
    if not 7 <= len(digits) <= 15:
        return ""
    return normalized


def format_indian_phone(value) -> str:
    """Return a display phone number with one Indian country-code prefix."""
    phone = clean_text(value)
    if not phone:
        return ""
    if re.match(r"^\+91(?:\s|$)", phone):
        return "+91 " + re.sub(r"^\+91\s*", "", phone).strip()
    if phone.startswith("+91"):
        return "+91 " + phone[3:].strip()
    return f"+91 {phone}"


def normalize_https_url(value, *, add_scheme: bool = False) -> str:
    candidate = clean_text(value)
    if not candidate:
        return ""
    if add_scheme and "://" not in candidate:
        if re.match(r"^[a-z][a-z0-9+.-]*:", candidate, re.I):
            return ""
        candidate = "https://" + candidate.lstrip("/")
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return ""
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        return ""
    if parsed.username or parsed.password or any(ord(ch) < 32 for ch in candidate):
        return ""
    return candidate


def normalize_form_values(
    raw: dict, *, organization: str = "", website: str = ""
) -> dict:
    first_name = clean_text(raw.get("firstName"))
    last_name = clean_text(raw.get("lastName"))
    manager_first = clean_text(raw.get("managerFirstName"))
    manager_last = clean_text(raw.get("managerLastName"))
    manager2_first = clean_text(raw.get("manager2FirstName"))
    manager2_last = clean_text(raw.get("manager2LastName"))

    employee_email = safe_email(raw.get("email"))
    manager_email = safe_email(raw.get("managerEmail"))
    manager2_email = safe_email(raw.get("manager2Email"))
    website_href = normalize_https_url(website, add_scheme=True)
    return {
        "fullName": " ".join(part for part in (first_name, last_name) if part),
        "designation": clean_text(raw.get("designation")),
        "phone": format_indian_phone(raw.get("phone")),
        "phoneHref": normalize_tel(format_indian_phone(raw.get("phone"))),
        "email": employee_email,
        "emailHref": employee_email,
        "organization": clean_text(organization),
        "address": clean_text(raw.get("address")),
        "websiteLabel": (
            re.sub(r"^https?://", "", clean_text(website), flags=re.I)
            if website_href
            else ""
        ),
        "websiteHref": website_href,
        "managerFullName": " ".join(
            part for part in (manager_first, manager_last) if part
        ),
        "managerDesignation": clean_text(raw.get("managerDesignation")),
        "managerEmail": manager_email,
        "managerEmailHref": manager_email,
        "managerPhone": format_indian_phone(raw.get("managerPhone")),
        "managerPhoneHref": normalize_tel(format_indian_phone(raw.get("managerPhone"))),
        "manager2FullName": " ".join(
            part for part in (manager2_first, manager2_last) if part
        ),
        "manager2Designation": clean_text(raw.get("manager2Designation")),
        "manager2Email": manager2_email,
        "manager2EmailHref": manager2_email,
        "manager2Phone": format_indian_phone(raw.get("manager2Phone")),
        "manager2PhoneHref": normalize_tel(format_indian_phone(raw.get("manager2Phone"))),
    }


def _contact_row(label: str, display: str, href: str = "") -> str:
    if not display:
        return ""
    content = escape_html(display).replace("\n", "<br>")
    if href:
        content = (
            f'<a href="{escape_html(href)}" '
            f'style="color:{BRAND["link"]};text-decoration:none;">{content}</a>'
        )
    return (
        "<tr>"
        f'<td width="20" style="width:20px;padding:1px 8px 1px 0;vertical-align:top;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:10px;line-height:15px;'
        f'font-weight:700;color:{BRAND["maroon"]};">{escape_html(label)}:</td>'
        f'<td style="padding:1px 0;vertical-align:top;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:10px;line-height:15px;color:{BRAND["muted"]};word-break:break-word;">'
        f"{content}</td></tr>"
    )


def _manager_panel(values: dict, level: int) -> str:
    prefix = "manager" if level == 1 else "manager2"
    name = values.get(f"{prefix}FullName") or ""
    title = values.get(f"{prefix}Designation") or ""
    email = values.get(f"{prefix}Email") or ""
    email_href = values.get(f"{prefix}EmailHref") or ""
    phone = values.get(f"{prefix}Phone") or ""
    phone_href = values.get(f"{prefix}PhoneHref") or ""
    if not any((name, title, email, phone)):
        return ""
    identity = ""
    if name:
        identity += (
            f'<tr><td style="padding:0 0 1px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:11px;line-height:15px;font-weight:700;color:{BRAND["charcoal"]};'
            f'word-break:break-word;">{escape_html(name)}</td></tr>'
        )
    if title:
        identity += (
            f'<tr><td style="padding:0 0 4px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:10px;line-height:14px;color:{BRAND["muted"]};'
            f'word-break:break-word;">{escape_html(title)}</td></tr>'
        )
    contacts = (
        _contact_row("E", email, f"mailto:{email_href}" if email_href else "")
        + _contact_row("P", phone, f"tel:{phone_href}" if phone_href else "")
    )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'width="100%" style="width:100%;border-collapse:collapse;">'
        f'<tr><td style="padding:0 0 4px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:9px;line-height:13px;font-weight:700;letter-spacing:.5px;'
        f'color:{BRAND["maroon"]};">LEVEL {level} MANAGER</td></tr>'
        f"{identity}"
        f'<tr><td><table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="100%" style="width:100%;border-collapse:collapse;">{contacts}</table></td></tr>'
        "</table>"
    )


def manager_block(values: dict) -> str:
    panels = [_manager_panel(values, 1), _manager_panel(values, 2)]
    panels = [panel for panel in panels if panel]
    if not panels:
        return ""
    width = "50%" if len(panels) == 2 else "100%"
    cells = []
    for index, panel in enumerate(panels):
        padding = "0 8px 0 0" if index == 0 and len(panels) == 2 else (
            "0 0 0 8px" if len(panels) == 2 else "0"
        )
        cells.append(
            f'<td width="{width}" style="width:{width};padding:{padding};vertical-align:top;">'
            f"{panel}</td>"
        )
    return (
        '<tr><td colspan="2" style="padding:10px 0 0;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="100%" style="width:100%;border-collapse:collapse;"><tr>{"".join(cells)}</tr>'
        "</table></td></tr>"
    )


def contact_block(values: dict, *, team: str = "") -> str:
    identity = ""
    if values["fullName"]:
        identity += (
            f'<tr><td colspan="2" style="padding:0 0 2px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:16px;line-height:20px;font-weight:700;color:{BRAND["charcoal"]};'
            f'word-break:break-word;">{escape_html(values["fullName"])}</td></tr>'
        )
    meta = " | ".join(
        part for part in (values["designation"], values["organization"]) if part
    )
    if meta:
        identity += (
            f'<tr><td colspan="2" style="padding:0;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:11px;line-height:16px;color:{BRAND["muted"]};'
            f'word-break:break-word;">{escape_html(meta)}</td></tr>'
        )

    contact_rows = (
        _contact_row(
            "E",
            values["email"],
            f'mailto:{values["emailHref"]}' if values["emailHref"] else "",
        )
        + _contact_row("W", values["websiteLabel"], values["websiteHref"])
        + _contact_row(
            "P",
            values["phone"],
            f'tel:{values["phoneHref"]}' if values["phoneHref"] else "",
        )
        + _contact_row("A", values["address"])
    )
    manager_html = manager_block(values) if (team or "").lower() == "sales" else ""
    divider = ""
    if identity and (contact_rows or manager_html):
        divider = (
            '<tr><td colspan="2" style="padding:8px 0 7px;">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            f'width="54" style="width:54px;border-collapse:collapse;"><tr>'
            f'<td height="2" style="height:2px;line-height:2px;font-size:0;'
            f'background:{BRAND["maroon"]};">&nbsp;</td></tr></table></td></tr>'
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'width="100%" style="width:100%;border-collapse:collapse;">'
        f"{identity}{divider}{contact_rows}{manager_html}</table>"
    )


def _safe_asset_url(value) -> str:
    url = clean_text(value)
    if url.startswith("/static/"):
        return url
    return normalize_https_url(url)


def logo_cell(assets: dict) -> str:
    logo = _safe_asset_url(assets.get("logo"))
    if not logo:
        return ""
    width = max(40, min(int(assets.get("logoWidth") or 200), 230))
    height = max(1, int(assets.get("logoHeight") or round(width / 3)))
    image = (
        f'<img src="{escape_html(logo)}" width="{width}" height="{height}" '
        f'alt="{escape_html(assets.get("logoAlt") or "Organization logo")}" '
        f'style="display:block;margin:0 auto;border:0;outline:none;text-decoration:none;'
        f'width:{width}px;height:{height}px;" />'
    )
    href = normalize_https_url(assets.get("logoHref"))
    if href:
        image = (
            f'<a href="{escape_html(href)}" style="text-decoration:none;border:0;">'
            f"{image}</a>"
        )
    return (
        '<td width="230" style="width:230px;padding:14px 14px 14px 16px;'
        f'vertical-align:middle;text-align:center;border-left:1px solid {BRAND["line"]};">'
        f"{image}</td>"
    )


def social_row(socials: list[dict]) -> str:
    if not socials:
        return ""
    cells = []
    for index, social in enumerate(socials):
        href = normalize_https_url(social.get("href"))
        icon = normalize_https_url(social.get("icon"))
        if not href or not icon:
            continue
        padding = "0 8px 0 0" if index < len(socials) - 1 else "0"
        cells.append(
            f'<td width="32" style="width:32px;padding:{padding};vertical-align:middle;">'
            f'<a href="{escape_html(href)}" style="display:block;text-decoration:none;border:0;">'
            f'<img src="{escape_html(icon)}" width="22" height="22" '
            f'alt="{escape_html(social.get("alt") or "Social profile")}" '
            'style="display:block;width:22px;height:22px;border:0;outline:none;'
            'text-decoration:none;" /></a></td>'
        )
    if not cells:
        return ""
    return (
        '<tr><td colspan="2" style="padding:9px 14px 10px;border-top:1px solid #EEE4E7;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-collapse:collapse;"><tr>{"".join(cells)}</tr></table></td></tr>'
    )


def banner_row(assets: dict) -> str:
    banner = _safe_asset_url(assets.get("banner"))
    if not banner:
        return ""
    width = max(1, min(int(assets.get("bannerWidth") or 600), 600))
    height = max(1, int(assets.get("bannerHeight") or 110))
    image = (
        f'<img src="{escape_html(banner)}" width="{width}" height="{height}" '
        f'alt="{escape_html(assets.get("bannerAlt") or "Arvind campaign")}" '
        f'style="display:block;width:{width}px;max-width:100%;height:auto;border:0;'
        'outline:none;text-decoration:none;" />'
    )
    href = normalize_https_url(assets.get("bannerHref"))
    if href:
        image = (
            f'<a href="{escape_html(href)}" style="display:block;text-decoration:none;border:0;">'
            f"{image}</a>"
        )
    return (
        '<tr><td colspan="2" style="padding:8px 0 0;line-height:0;font-size:0;">'
        f"{image}</td></tr>"
    )


def _build_branded_template(
    values: dict, assets: dict, *, team: str, width: int, include_banner: bool
) -> str:
    logo = logo_cell(assets)
    detail_width = width - 230 if logo else width
    detail_cell = (
        f'<td width="{detail_width}"'
        + (' colspan="2"' if not logo else "")
        + f' style="width:{detail_width}px;padding:14px 16px;vertical-align:top;'
        f'background:#ffffff;">{contact_block(values, team=team)}</td>'
    )
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="{width}" style="width:{width}px;max-width:{width}px;border-collapse:collapse;'
        f'font-family:Arial,Helvetica,sans-serif;background:#ffffff;color:{BRAND["muted"]};">'
        f"<tr>{detail_cell}{logo}</tr>"
        f'{social_row(assets.get("socials") or [])}'
        f'{banner_row(assets) if include_banner else ""}'
        "</table>"
    )


def build_standard_template(values: dict, assets: dict, *, team: str = "") -> str:
    return _build_branded_template(
        values, assets, team=team, width=600, include_banner=True
    )


def build_compact_template(values: dict, assets: dict, *, team: str = "") -> str:
    return _build_branded_template(
        values, assets, team=team, width=560, include_banner=False
    )


def build_minimal_template(values: dict, *, team: str = "") -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'width="420" style="width:420px;max-width:420px;border-collapse:collapse;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        f'<tr><td style="padding:8px 0 8px 34px;">{contact_block(values, team=team)}</td></tr>'
        "</table>"
    )


def _logo_markup(assets: dict, *, width: int = 190) -> str:
    logo = _safe_asset_url(assets.get("logo"))
    if not logo:
        return ""
    source_width = max(40, int(assets.get("logoWidth") or width))
    source_height = max(1, int(assets.get("logoHeight") or round(source_width / 3)))
    display_width = max(40, min(width, source_width))
    display_height = max(1, round(display_width * source_height / source_width))
    image = (
        f'<img src="{escape_html(logo)}" width="{display_width}" height="{display_height}" '
        f'alt="{escape_html(assets.get("logoAlt") or "Organization logo")}" '
        f'style="display:block;border:0;outline:none;text-decoration:none;'
        f'width:{display_width}px;height:{display_height}px;" />'
    )
    href = normalize_https_url(assets.get("logoHref"))
    if href:
        return f'<a href="{escape_html(href)}" style="text-decoration:none;border:0;">{image}</a>'
    return image


def _linked_text(label: str, href: str = "", *, color: str | None = None) -> str:
    safe_label = escape_html(label)
    if not href:
        return safe_label
    return (
        f'<a href="{escape_html(href)}" style="color:{color or BRAND["charcoal"]};'
        f'text-decoration:none;">{safe_label}</a>'
    )


def _new_template_managers(values: dict, team: str) -> str:
    return manager_block(values) if (team or "").lower() == "sales" else ""


def build_logo_header_template(values: dict, assets: dict, *, team: str = "") -> str:
    logo = _logo_markup(assets, width=220)
    name = escape_html(values["fullName"])
    designation = escape_html(values["designation"])
    identity_parts = []
    if name:
        identity_parts.append(f'<strong style="color:{BRAND["charcoal"]};">{name}</strong>')
    if designation:
        identity_parts.append(designation)
    identity = "&nbsp; | &nbsp;".join(identity_parts)

    contacts = []
    if values["phone"]:
        contacts.append(
            "Mobile: "
            + _linked_text(
                values["phone"],
                f'tel:{values["phoneHref"]}' if values["phoneHref"] else "",
            )
        )
    if values["email"]:
        contacts.append(
            "Email: "
            + _linked_text(
                values["email"],
                f'mailto:{values["emailHref"]}' if values["emailHref"] else "",
            )
        )
    contact_line = "&nbsp; | &nbsp;".join(contacts)

    detail_rows = ""
    for content in (identity, contact_line, escape_html(values["address"])):
        if content:
            detail_rows += (
                f'<tr><td colspan="2" style="padding:0 0 3px 34px;font-size:12px;line-height:17px;'
                f'color:{BRAND["muted"]};">{content}</td></tr>'
            )
    if values["websiteLabel"]:
        detail_rows += (
            f'<tr><td colspan="2" style="padding:0 0 0 34px;font-size:12px;line-height:17px;'
            f'color:{BRAND["muted"]};">Web: '
            f'{_linked_text(values["websiteLabel"], values["websiteHref"], color=BRAND["maroon"])}</td></tr>'
        )
    logo_row = (
        f'<tr><td colspan="2" style="padding:18px 0 14px 34px;vertical-align:middle;">{logo}</td></tr>'
        if logo
        else ""
    )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" '
        f'style="width:600px;max-width:600px;border-collapse:collapse;background:#ffffff;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        f'{logo_row}{detail_rows}{social_row(assets.get("socials") or [])}'
        f'{_new_template_managers(values, team)}</table>'
    )


def build_logo_sidebar_template(values: dict, assets: dict, *, team: str = "") -> str:
    logo = _logo_markup(assets, width=135)
    header = ""
    if values["fullName"]:
        header += (
            f'<tr><td colspan="2" style="padding:12px 0 0 18px;font-size:17px;line-height:21px;'
            f'font-weight:700;color:{BRAND["charcoal"]};">{escape_html(values["fullName"])}</td></tr>'
        )
    if values["designation"]:
        header += (
            f'<tr><td colspan="2" style="padding:1px 0 8px 18px;border-bottom:1px dotted {BRAND["line"]};'
            f'font-size:14px;line-height:19px;color:{BRAND["maroon"]};">'
            f'{escape_html(values["designation"])}</td></tr>'
        )
    rows = ""
    contact_values = (
        ("T", values["phone"], f'tel:{values["phoneHref"]}' if values["phoneHref"] else ""),
        ("E", values["email"], f'mailto:{values["emailHref"]}' if values["emailHref"] else ""),
        ("W", values["websiteLabel"], values["websiteHref"]),
        ("A", values["address"], ""),
    )
    for label, value, href in contact_values:
        if value:
            rows += (
                f'<tr><td style="padding:0 5px 2px 0;font-size:11px;font-weight:700;'
                f'color:{BRAND["maroon"]};vertical-align:top;">{label}:</td>'
                f'<td style="padding:0 0 2px;font-size:12px;line-height:16px;color:{BRAND["charcoal"]};">'
                f'{_linked_text(value, href)}</td></tr>'
            )
    logo_cell_html = (
        f'<td width="170" style="width:170px;padding:14px 20px 12px 20px;vertical-align:middle;">{logo}</td>'
        if logo
        else ""
    )
    detail_width = 430 if logo else 600
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" '
        f'style="width:600px;max-width:600px;border-collapse:collapse;background:#ffffff;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        f'{header}<tr>{logo_cell_html}<td width="{detail_width}" style="width:{detail_width}px;'
        f'padding:14px 0 12px;vertical-align:top;"><table role="presentation" cellpadding="0" '
        f'cellspacing="0" border="0" style="border-collapse:collapse;">{rows}</table></td></tr>'
        f'{social_row(assets.get("socials") or [])}{_new_template_managers(values, team)}</table>'
    )


def build_logo_profile_template(values: dict, assets: dict, *, team: str = "") -> str:
    logo = _logo_markup(assets, width=150)
    detail_rows = ""
    if values["fullName"]:
        detail_rows += (
            f'<tr><td style="padding:0 0 2px;font-size:22px;line-height:26px;font-weight:700;'
            f'color:{BRAND["charcoal"]};">{escape_html(values["fullName"])}</td></tr>'
        )
    for value in (values["designation"], values["organization"]):
        if value:
            detail_rows += (
                f'<tr><td style="padding:0 0 2px;font-size:15px;line-height:19px;'
                f'color:{BRAND["maroon"]};">{escape_html(value)}</td></tr>'
            )
    contact_rows = ""
    for symbol, value, href in (
        ("P", values["phone"], f'tel:{values["phoneHref"]}' if values["phoneHref"] else ""),
        ("E", values["email"], f'mailto:{values["emailHref"]}' if values["emailHref"] else ""),
        ("W", values["websiteLabel"], values["websiteHref"]),
    ):
        if value:
            contact_rows += (
                f'<tr><td width="24" style="width:24px;padding:2px 8px 2px 0;font-size:11px;'
                f'font-weight:700;color:{BRAND["maroon"]};vertical-align:top;">{symbol}</td>'
                f'<td style="padding:2px 0;font-size:13px;line-height:18px;color:{BRAND["charcoal"]};">'
                f'{_linked_text(value, href)}</td></tr>'
            )
    logo_panel = (
        f'<td width="190" style="width:190px;padding:20px;vertical-align:middle;text-align:center;'
        f'border:2px solid {BRAND["maroon"]};border-radius:100px;">{logo}</td>'
        if logo
        else ""
    )
    address_row = ""
    if values["address"]:
        address_row = (
            f'<tr><td colspan="2" style="padding:8px 16px;background:{BRAND["charcoal"]};'
            f'border-bottom:4px solid {BRAND["maroon"]};font-size:13px;line-height:18px;'
            f'text-align:center;color:#ffffff;">{escape_html(values["address"])}</td></tr>'
        )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" '
        f'style="width:600px;max-width:600px;border-collapse:collapse;background:#ffffff;'
        f'font-family:Arial,Helvetica,sans-serif;color:{BRAND["muted"]};">'
        f'<tr>{logo_panel}<td style="padding:12px 0 12px 28px;vertical-align:middle;'
        f'border-left:3px solid {BRAND["maroon"]};"><table role="presentation" cellpadding="0" '
        f'cellspacing="0" border="0" style="border-collapse:collapse;">{detail_rows}'
        f'<tr><td style="padding-top:10px;"><table role="presentation" cellpadding="0" cellspacing="0" '
        f'border="0" style="border-collapse:collapse;">{contact_rows}</table></td></tr></table></td></tr>'
        f'{address_row}{social_row(assets.get("socials") or [])}'
        f'{_new_template_managers(values, team)}</table>'
    )


def build_signature_html(
    template_id: str, raw_values: dict, asset_urls: dict, *, team: str = ""
) -> str:
    values = normalize_form_values(
        raw_values,
        organization=asset_urls.get("organization") or "",
        website=asset_urls.get("website") or "",
    )
    assets = {
        key: asset_urls.get(key)
        for key in (
            "logo",
            "banner",
            "logoWidth",
            "logoHeight",
            "bannerWidth",
            "bannerHeight",
            "logoAlt",
            "bannerAlt",
            "logoHref",
            "bannerHref",
            "socials",
        )
    }
    if template_id == "compact":
        return build_compact_template(values, assets, team=team)
    if template_id == "minimal":
        return build_minimal_template(values, team=team)
    if template_id == "logo-header":
        return build_logo_header_template(values, assets, team=team)
    if template_id == "logo-sidebar":
        return build_logo_sidebar_template(values, assets, team=team)
    if template_id == "logo-profile":
        return build_logo_profile_template(values, assets, team=team)
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
        fallback_path = static_root() / fallback
        if fallback_path.is_file():
            return fallback_path
    return candidate if candidate.exists() else None


def _resolved_relative_asset(rel_path: str | None) -> str:
    if not rel_path:
        return ""
    rel = rel_path.replace("\\", "/").lstrip("/")
    resolved = resolve_static_path(rel)
    if not resolved or not resolved.is_file():
        return ""
    try:
        return str(resolved.relative_to(static_root())).replace("\\", "/")
    except ValueError:
        return ""


def preview_asset_url(rel_path: str | None) -> str:
    rel = _resolved_relative_asset(rel_path)
    return url_for("static", filename=rel) if rel else ""


def email_asset_url(rel_path: str | None) -> str:
    rel = _resolved_relative_asset(rel_path)
    if not rel:
        return ""
    if Path(rel).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif"}:
        return ""
    configured = current_app.config.get("PUBLIC_ASSET_BASE_URL") or ""
    if not configured:
        app_base = current_app.config.get("APP_BASE_URL") or ""
        configured = app_base if normalize_https_url(app_base) else ""
    origin = normalize_https_url(configured)
    if not origin:
        return ""
    return f'{origin.rstrip("/")}/static/{quote(rel, safe="/")}'


def _png_dimensions(path: Path | None) -> tuple[int, int] | None:
    if not path or not path.is_file() or path.suffix.lower() != ".png":
        return None
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", header[16:24])
    except (OSError, struct.error):
        return None


def organization_social_links(slug: str, label: str) -> list[dict]:
    approved = ORGANIZATION_SOCIAL_LINKS.get(slug, {})
    socials = []
    for platform in ("facebook", "x", "linkedin", "youtube", "instagram"):
        href = normalize_https_url(approved.get(platform))
        settings = SOCIAL_PLATFORM_CONFIG.get(platform) or {}
        icon = normalize_https_url(settings.get("icon"))
        if not href or not icon:
            continue
        socials.append(
            {
                "platform": platform,
                "href": href,
                "icon": icon,
                "alt": f'{label or "Arvind"} on {settings.get("label") or platform.title()}',
            }
        )
    return socials


def _org_value(org, name: str, default=None):
    if org is None:
        return default
    if isinstance(org, dict):
        return org.get(name, default)
    return getattr(org, name, default)


def assets_from_org(org, *, for_email: bool = False) -> dict:
    """Return only backend-approved organization branding configuration."""
    slug = clean_text(_org_value(org, "slug", "arvind-limited"))
    label = clean_text(_org_value(org, "label", "Arvind Limited"))
    organization = clean_text(_org_value(org, "organization", label))
    website = clean_text(_org_value(org, "website", "www.arvind.com"))
    logo = _org_value(org, "logo_path", "assets/arvind-company-logo-transparent.png")
    banner = _org_value(org, "banner_path")
    logo_width = int(_org_value(org, "logo_width", 230) or 230)

    logo_path = resolve_static_path(logo)
    banner_path = resolve_static_path(banner) if banner else None
    logo_dimensions = _png_dimensions(logo_path)
    banner_dimensions = _png_dimensions(banner_path)
    display_logo_width = max(40, min(logo_width, 230))
    logo_height = (
        round(display_logo_width * logo_dimensions[1] / logo_dimensions[0])
        if logo_dimensions
        else round(display_logo_width / 3)
    )
    banner_width = min(banner_dimensions[0], 600) if banner_dimensions else 600
    banner_height = (
        round(banner_width * banner_dimensions[1] / banner_dimensions[0])
        if banner_dimensions
        else 110
    )

    asset_url = email_asset_url if for_email else preview_asset_url
    website_href = normalize_https_url(website, add_scheme=True)
    banner_href = normalize_https_url(ORGANIZATION_BANNER_LINKS.get(slug))
    return {
        "slug": slug,
        "organization": organization,
        "website": website,
        "logo": asset_url(logo),
        "banner": asset_url(banner) if banner else "",
        "logoWidth": display_logo_width,
        "logoHeight": logo_height,
        "bannerWidth": banner_width,
        "bannerHeight": banner_height,
        "logoAlt": f"{label} logo",
        "bannerAlt": f"{label} campaign",
        "logoHref": website_href,
        "bannerHref": banner_href,
        "socials": organization_social_links(slug, label),
    }
