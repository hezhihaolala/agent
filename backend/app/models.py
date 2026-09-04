from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return str(uuid4())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["AdminSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[AdminUser] = relationship(back_populates="sessions")


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), index=True)
    gender: Mapped[str] = mapped_column(String(20), default="unknown")
    birth_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    death_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    native_place: Mapped[str | None] = mapped_column(String(200), nullable=True)
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    relative_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    era: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provenance: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str] = mapped_column(String(100), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    links: Mapped[list["SourceLink"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )


class SourceLink(Base):
    __tablename__ = "source_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = relationship(back_populates="links")


class ChangeDraft(Base):
    __tablename__ = "change_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    raw_input: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(String(30), default="v1")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
