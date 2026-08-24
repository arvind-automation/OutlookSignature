from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    grade = db.Column(db.String(32), nullable=True)
    team = db.Column(db.String(32), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    saved_signature = db.relationship(
        "SavedSignature",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_logs = db.relationship("AuditLog", back_populates="user")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_public_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name or "",
            "last_name": self.last_name or "",
            "grade": self.grade or "",
            "team": self.team or "",
        }


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    label = db.Column(db.String(255), nullable=False)
    organization = db.Column(db.String(255), nullable=False)
    website = db.Column(db.String(255), nullable=False)
    logo_path = db.Column(db.String(512), nullable=False)
    banner_path = db.Column(db.String(512), nullable=True)
    watermark_path = db.Column(db.String(512), nullable=False)
    logo_bg = db.Column(db.String(32), nullable=False, default="#ffffff")
    logo_width = db.Column(db.Integer, nullable=False, default=230)
    default_address = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    saved_signatures = db.relationship("SavedSignature", back_populates="organization")

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "label": self.label,
            "organization": self.organization,
            "website": self.website,
            "logo": self.logo_path,
            "banner": self.banner_path,
            "watermark": self.watermark_path,
            "logoBg": self.logo_bg,
            "logoWidth": self.logo_width,
            "defaultAddress": self.default_address or "",
        }


class SavedSignature(db.Model):
    __tablename__ = "saved_signatures"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id = db.Column(db.String(32), nullable=False, default="standard")
    first_name = db.Column(db.String(120), nullable=False, default="")
    last_name = db.Column(db.String(120), nullable=False, default="")
    email = db.Column(db.String(255), nullable=False, default="")
    designation = db.Column(db.String(255), nullable=False, default="")
    phone = db.Column(db.String(64), nullable=False, default="")
    organization_name = db.Column(db.String(255), nullable=False, default="")
    website = db.Column(db.String(255), nullable=False, default="")
    address = db.Column(db.Text, nullable=False, default="")
    manager_first_name = db.Column(db.String(120), nullable=False, default="")
    manager_last_name = db.Column(db.String(120), nullable=False, default="")
    manager_designation = db.Column(db.String(255), nullable=False, default="")
    manager_email = db.Column(db.String(255), nullable=False, default="")
    manager_phone = db.Column(db.String(64), nullable=False, default="")
    manager2_first_name = db.Column(db.String(120), nullable=False, default="")
    manager2_last_name = db.Column(db.String(120), nullable=False, default="")
    manager2_designation = db.Column(db.String(255), nullable=False, default="")
    manager2_email = db.Column(db.String(255), nullable=False, default="")
    manager2_phone = db.Column(db.String(64), nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="saved_signature")
    organization = db.relationship("Organization", back_populates="saved_signatures")

    def to_form_dict(self):
        return {
            "company": self.organization.slug if self.organization else "",
            "firstName": self.first_name or "",
            "lastName": self.last_name or "",
            "email": self.email or "",
            "designation": self.designation or "",
            "phone": self.phone or "",
            "organization": self.organization_name or "",
            "website": self.website or "",
            "address": self.address or "",
            "managerFirstName": self.manager_first_name or "",
            "managerLastName": self.manager_last_name or "",
            "managerEmail": self.manager_email or "",
            "templateId": self.template_id or "standard",
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    details = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="audit_logs")
