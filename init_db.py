#!/usr/bin/env python3
"""Database bootstrap: wait, create, seed, verify — with guardrails and edge-case handling."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash

# Ensure project root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [init_db] %(levelname)s %(message)s",
)
log = logging.getLogger("init_db")

REQUIRED_ORG_SLUGS = (
    "anup-engineering",
    "arvind-smartspaces",
    "arvind-fashions",
    "arvind-limited",
)
DEMO_EMAIL = "nazeer.ahmed@arvind.in"
DEMO_PASSWORD = "123456789"
ADMIN_SEED_EMAILS = (DEMO_EMAIL,)
MAX_WAIT_ATTEMPTS = 40
WAIT_SECONDS = 3


def get_database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        log.error("DATABASE_URL is missing or empty. Copy .env.example to .env and set it.")
        sys.exit(2)
    if not url.startswith("mysql"):
        log.error("DATABASE_URL must be a MySQL URL (mysql+pymysql://...). Got: %s", url.split("@")[-1])
        sys.exit(2)
    return url


def parse_db_parts(url: str):
    parsed = urlparse(url.replace("mysql+pymysql://", "mysql://", 1))
    db_name = (parsed.path or "").lstrip("/")
    if not db_name:
        log.error("DATABASE_URL has no database name (path). Example: .../digitalsignature_arvind")
        sys.exit(2)
    server_url = urlunparse(
        (
            "mysql+pymysql",
            parsed.netloc,
            "/",
            "",
            "",
            "",
        )
    )
    return db_name, server_url, url


def wait_for_mysql(server_url: str) -> None:
    log.info("Waiting for MySQL to become available...")
    last_err = None
    for attempt in range(1, MAX_WAIT_ATTEMPTS + 1):
        try:
            engine = create_engine(server_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            log.info("MySQL is ready (attempt %s).", attempt)
            return
        except OperationalError as exc:
            last_err = exc
            log.warning("MySQL not ready (attempt %s/%s): %s", attempt, MAX_WAIT_ATTEMPTS, exc.orig if hasattr(exc, "orig") else exc)
            time.sleep(WAIT_SECONDS)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log.warning("MySQL connect error (attempt %s/%s): %s", attempt, MAX_WAIT_ATTEMPTS, exc)
            time.sleep(WAIT_SECONDS)
    log.error("Could not connect to MySQL after %s attempts. Last error: %s", MAX_WAIT_ATTEMPTS, last_err)
    sys.exit(3)


def ensure_database(server_url: str, db_name: str) -> None:
    log.info("Ensuring database `%s` exists...", db_name)
    engine = create_engine(server_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()
    engine.dispose()
    log.info("Database `%s` is present.", db_name)


def create_app_context():
    from app import create_app

    return create_app()


def reset_tables(app) -> None:
    flask_env = os.getenv("FLASK_ENV", "development").lower()
    allow = os.getenv("INIT_DB_ALLOW_RESET", "0") == "1" or os.getenv("INIT_DB_I_UNDERSTAND", "0") == "1"
    if flask_env == "production":
        log.error("Refusing --reset in production (FLASK_ENV=production).")
        sys.exit(4)
    if not allow:
        log.error(
            "Reset blocked. Set INIT_DB_ALLOW_RESET=1 (or INIT_DB_I_UNDERSTAND=1) to drop tables."
        )
        sys.exit(4)

    from app.extensions import db

    log.warning("Dropping all tables (--reset)...")
    with app.app_context():
        db.drop_all()
        db.create_all()
        ensure_manager_columns(app)
        ensure_user_columns(app)
        ensure_organization_columns(app)
    log.info("Tables recreated.")


def create_tables(app) -> None:
    from app.extensions import db

    log.info("Creating tables if missing...")
    with app.app_context():
        db.create_all()
        ensure_manager_columns(app)
        ensure_user_columns(app)
        ensure_organization_columns(app)
    log.info("Tables ready.")


def ensure_user_columns(app) -> None:
    """Idempotently add user columns on existing DBs."""
    from app.extensions import db

    columns = {
        "is_admin": "TINYINT(1) NOT NULL DEFAULT 0",
        "grade": "VARCHAR(32) NULL",
    }

    with app.app_context():
        existing = {
            row[0]
            for row in db.session.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'"
                )
            ).fetchall()
        }
        for name, ddl in columns.items():
            if name in existing:
                continue
            log.info("Adding column users.%s", name)
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        db.session.commit()


def ensure_manager_columns(app) -> None:
    """Idempotently add Sales manager columns to saved_signatures on existing DBs."""
    from app.extensions import db

    columns = {
        "manager_first_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "manager_last_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "manager_designation": "VARCHAR(255) NOT NULL DEFAULT ''",
        "manager_email": "VARCHAR(255) NOT NULL DEFAULT ''",
        "manager_phone": "VARCHAR(64) NOT NULL DEFAULT ''",
        "manager2_first_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "manager2_last_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "manager2_designation": "VARCHAR(255) NOT NULL DEFAULT ''",
        "manager2_email": "VARCHAR(255) NOT NULL DEFAULT ''",
        "manager2_phone": "VARCHAR(64) NOT NULL DEFAULT ''",
    }

    with app.app_context():
        existing = {
            row[0]
            for row in db.session.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'saved_signatures'"
                )
            ).fetchall()
        }
        for name, ddl in columns.items():
            if name in existing:
                continue
            log.info("Adding column saved_signatures.%s", name)
            db.session.execute(text(f"ALTER TABLE saved_signatures ADD COLUMN {name} {ddl}"))
        db.session.commit()


def ensure_organization_columns(app) -> None:
    """Idempotently add organization defaults on existing databases."""
    from app.extensions import db

    columns = {
        "default_address": "TEXT NULL",
    }

    with app.app_context():
        existing = {
            row[0]
            for row in db.session.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'organizations'"
                )
            ).fetchall()
        }
        for name, ddl in columns.items():
            if name in existing:
                continue
            log.info("Adding column organizations.%s", name)
            db.session.execute(text(f"ALTER TABLE organizations ADD COLUMN {name} {ddl}"))
        db.session.commit()


def seed_organizations(app) -> int:
    from app.extensions import db
    from app.models import Organization
    from app.signatures import ORGANIZATION_SEEDS

    updated = 0
    with app.app_context():
        for seed in ORGANIZATION_SEEDS:
            org = Organization.query.filter_by(slug=seed["slug"]).first()
            if org is None:
                org = Organization(slug=seed["slug"])
                db.session.add(org)
                log.info("Inserting organization slug=%s", seed["slug"])
            else:
                log.info("Updating organization slug=%s to canonical seed values", seed["slug"])

            org.label = seed["label"]
            org.organization = seed["organization"]
            org.website = seed["website"]
            org.logo_path = seed["logo_path"]
            org.banner_path = seed["banner_path"]
            org.watermark_path = seed["watermark_path"]
            org.logo_bg = seed["logo_bg"]
            org.logo_width = seed["logo_width"]
            org.default_address = seed.get("default_address", "")
            updated += 1
        db.session.commit()
    return updated


def seed_demo_user(app) -> None:
    from app.extensions import db
    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email=DEMO_EMAIL).first()
        if user is None:
            user = User(email=DEMO_EMAIL, first_name="Nazeer", last_name="Ahmed")
            user.set_password(DEMO_PASSWORD)
            db.session.add(user)
            log.info("Inserted demo user %s", DEMO_EMAIL)
        else:
            # Update profile fields; keep team and do not touch saved signatures
            user.first_name = "Nazeer"
            user.last_name = "Ahmed"
            if not user.check_password(DEMO_PASSWORD):
                user.set_password(DEMO_PASSWORD)
            log.info("Updated demo user profile %s (team preserved: %s)", DEMO_EMAIL, user.team)
        db.session.commit()


def seed_admin_users(app) -> None:
    """Promote seeded admin emails; does not demote other existing admins."""
    from app.extensions import db
    from app.models import User

    with app.app_context():
        for email in ADMIN_SEED_EMAILS:
            email = (email or "").strip().lower()
            if not email:
                continue
            user = User.query.filter_by(email=email).first()
            if user is None:
                log.warning("Admin seed email not found, skipping: %s", email)
                continue
            if not user.is_admin:
                user.is_admin = True
                log.info("Granted is_admin to %s", email)
            else:
                log.info("Admin already set for %s", email)
        db.session.commit()


def verify_assets(app) -> list[str]:
    from app.signatures import ASSET_FALLBACKS, ORGANIZATION_SEEDS

    strict = os.getenv("INIT_DB_STRICT_ASSETS", "0") == "1"
    missing = []
    static_root = os.path.join(ROOT, "app", "static")

    paths = set()
    for seed in ORGANIZATION_SEEDS:
        paths.add(seed["logo_path"])
        paths.add(seed["watermark_path"])
        if seed.get("banner_path"):
            paths.add(seed["banner_path"])

    with app.app_context():
        for rel in sorted(paths):
            abs_path = os.path.join(static_root, rel.replace("/", os.sep))
            if os.path.isfile(abs_path):
                continue
            fallback = ASSET_FALLBACKS.get(rel)
            if fallback and os.path.isfile(os.path.join(static_root, fallback.replace("/", os.sep))):
                log.warning("Asset missing %s — fallback available: %s", rel, fallback)
                continue
            missing.append(rel)
            log.warning("Asset missing: %s", rel)

    if missing and strict:
        log.error("INIT_DB_STRICT_ASSETS=1 and missing assets: %s", ", ".join(missing))
        sys.exit(5)
    return missing


def integrity_checks(app) -> None:
    from app.extensions import db
    from app.models import Organization, User
    from app.signatures import ORGANIZATION_SEEDS

    with app.app_context():
        org_count = Organization.query.count()
        if org_count < len(REQUIRED_ORG_SLUGS):
            log.error("Expected at least %s orgs, found %s", len(REQUIRED_ORG_SLUGS), org_count)
            sys.exit(6)

        for slug in REQUIRED_ORG_SLUGS:
            org = Organization.query.filter_by(slug=slug).first()
            if org is None:
                log.error("Required organization slug missing: %s", slug)
                sys.exit(6)

        # Canonical field check for arvind-limited banner
        limited = Organization.query.filter_by(slug="arvind-limited").first()
        if not limited.banner_path:
            log.error("arvind-limited must have a banner_path")
            sys.exit(6)

        for seed in ORGANIZATION_SEEDS:
            if seed["slug"] == "arvind-limited":
                continue
            other = Organization.query.filter_by(slug=seed["slug"]).first()
            if other.banner_path is not None:
                log.error("Organization %s must have banner_path=NULL", seed["slug"])
                sys.exit(6)

        dup_slugs = db.session.execute(
            text(
                "SELECT slug, COUNT(*) c FROM organizations GROUP BY slug HAVING c > 1"
            )
        ).fetchall()
        if dup_slugs:
            log.error("Duplicate organization slugs: %s", dup_slugs)
            sys.exit(6)

        user = User.query.filter_by(email=DEMO_EMAIL).first()
        if user is None:
            log.error("Demo user missing: %s", DEMO_EMAIL)
            sys.exit(6)
        if not check_password_hash(user.password_hash, DEMO_PASSWORD):
            log.error("Demo user password hash does not verify")
            sys.exit(6)

        dup_emails = db.session.execute(
            text("SELECT email, COUNT(*) c FROM users GROUP BY email HAVING c > 1")
        ).fetchall()
        if dup_emails:
            log.error("Duplicate user emails: %s", dup_emails)
            sys.exit(6)

    log.info("Integrity checks passed.")


def write_init_audit(app, details: dict) -> None:
    from app.extensions import db
    from app.models import AuditLog

    with app.app_context():
        db.session.add(
            AuditLog(
                user_id=None,
                action="db_initialized",
                details=details,
                ip_address="init_db",
            )
        )
        db.session.commit()
    log.info("Wrote audit log db_initialized.")


def run_check_only(app) -> None:
    log.info("Running --check-only (no writes)...")
    from app.extensions import db

    with app.app_context():
        db.session.execute(text("SELECT 1"))
    verify_assets(app)
    integrity_checks(app)
    log.info("Check-only completed successfully.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Initialize Arvind Signature Generator database")
    parser.add_argument("--check-only", action="store_true", help="Connectivity + integrity only")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate tables (guarded)")
    args = parser.parse_args(argv)

    url = get_database_url()
    db_name, server_url, full_url = parse_db_parts(url)
    # Prefer connecting to server without DB for create; fall back to full URL wait
    wait_for_mysql(server_url)

    if args.check_only:
        app = create_app_context()
        run_check_only(app)
        return 0

    ensure_database(server_url, db_name)
    app = create_app_context()

    if args.reset:
        reset_tables(app)
    else:
        create_tables(app)

    org_count = seed_organizations(app)
    seed_demo_user(app)
    seed_admin_users(app)
    missing_assets = verify_assets(app)
    integrity_checks(app)
    write_init_audit(
        app,
        {
            "orgs_seeded": org_count,
            "demo_user": DEMO_EMAIL,
            "missing_assets": missing_assets,
            "reset": bool(args.reset),
        },
    )
    log.info("Database initialization complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        log.exception("Unexpected failure during init_db")
        raise SystemExit(1)
