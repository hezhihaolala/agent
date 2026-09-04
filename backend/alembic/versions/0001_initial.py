"""Initial genealogy schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("admin_users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("username", sa.String(100), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("username"))
    op.create_index("ix_admin_users_username", "admin_users", ["username"])
    op.create_table("persons", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("gender", sa.String(20), nullable=False), sa.Column("birth_date", sa.String(50)), sa.Column("death_date", sa.String(50)), sa.Column("native_place", sa.String(200)), sa.Column("biography", sa.Text()), sa.Column("verification_status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_persons_name", "persons", ["name"])
    op.create_table("sources", sa.Column("id", sa.String(36), primary_key=True), sa.Column("title", sa.String(200), nullable=False), sa.Column("source_type", sa.String(30), nullable=False), sa.Column("era", sa.String(100)), sa.Column("provenance", sa.String(300)), sa.Column("notes", sa.Text()), sa.Column("verification_status", sa.String(30), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_name", sa.String(100), nullable=False), sa.Column("media_type", sa.String(100), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("storage_name"))
    op.create_index("ix_sources_source_type", "sources", ["source_type"])
    op.create_index("ix_sources_sha256", "sources", ["sha256"])
    op.create_index("ix_sources_created_at", "sources", ["created_at"])
    op.create_table("admin_sessions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("csrf_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("token_hash"))
    op.create_index("ix_admin_sessions_user_id", "admin_sessions", ["user_id"])
    op.create_index("ix_admin_sessions_token_hash", "admin_sessions", ["token_hash"])
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])
    op.create_table("relationships", sa.Column("id", sa.String(36), primary_key=True), sa.Column("kind", sa.String(20), nullable=False), sa.Column("person_id", sa.String(36), sa.ForeignKey("persons.id"), nullable=False), sa.Column("relative_id", sa.String(36), sa.ForeignKey("persons.id"), nullable=False), sa.Column("verification_status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_relationships_kind", "relationships", ["kind"])
    op.create_index("ix_relationships_person_id", "relationships", ["person_id"])
    op.create_index("ix_relationships_relative_id", "relationships", ["relative_id"])
    op.create_table("audit_logs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("admin_users.id"), nullable=False), sa.Column("action", sa.String(100), nullable=False), sa.Column("entity_type", sa.String(50), nullable=False), sa.Column("entity_id", sa.String(36), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_table("source_links", sa.Column("id", sa.String(36), primary_key=True), sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False), sa.Column("entity_type", sa.String(30), nullable=False), sa.Column("entity_id", sa.String(36), nullable=False), sa.Column("field_name", sa.String(100)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_source_links_source_id", "source_links", ["source_id"])
    op.create_index("ix_source_links_entity_type", "source_links", ["entity_type"])
    op.create_index("ix_source_links_entity_id", "source_links", ["entity_id"])
    op.create_table("change_drafts", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("admin_users.id"), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("raw_input", sa.Text(), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("prompt_version", sa.String(30), nullable=False), sa.Column("model_name", sa.String(100)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("confirmed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_change_drafts_user_id", "change_drafts", ["user_id"])
    op.create_index("ix_change_drafts_status", "change_drafts", ["status"])
    op.create_index("ix_change_drafts_created_at", "change_drafts", ["created_at"])


def downgrade() -> None:
    for table in ["change_drafts", "source_links", "audit_logs", "relationships", "admin_sessions", "sources", "persons", "admin_users"]:
        op.drop_table(table)
