"""Add relationship inference fields."""

from alembic import op
import sqlalchemy as sa


revision = "0002_relationship_inference_network"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("persons", sa.Column("birth_place", sa.String(200), nullable=True))
    op.add_column("persons", sa.Column("courtesy_name", sa.String(100), nullable=True))
    op.add_column("persons", sa.Column("art_name", sa.String(100), nullable=True))
    op.add_column("persons", sa.Column("aliases", sa.String(200), nullable=True))
    op.add_column("persons", sa.Column("generation_name", sa.String(100), nullable=True))
    op.add_column("persons", sa.Column("family_rank", sa.String(100), nullable=True))
    op.add_column("persons", sa.Column("occupation", sa.String(100), nullable=True))
    op.add_column(
        "relationships", sa.Column("sibling_type", sa.String(20), nullable=True)
    )
    op.execute(
        "UPDATE relationships SET sibling_type = 'unknown' "
        "WHERE kind = 'sibling' AND sibling_type IS NULL"
    )


def downgrade() -> None:
    op.drop_column("relationships", "sibling_type")
    op.drop_column("persons", "occupation")
    op.drop_column("persons", "family_rank")
    op.drop_column("persons", "generation_name")
    op.drop_column("persons", "aliases")
    op.drop_column("persons", "art_name")
    op.drop_column("persons", "courtesy_name")
    op.drop_column("persons", "birth_place")
