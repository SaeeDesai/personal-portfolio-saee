
"""Add campaign management.

Revision ID: e8b4c2d91a60
Revises: cd6783227cf3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e8b4c2d91a60"
down_revision: Union[str, Sequence[str], None] = "cd6783227cf3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "public_token",
            sa.String(length=46),
            nullable=False,
        ),
        sa.Column(
            "company",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "public_token",
            name="uq_campaigns_public_token",
        ),
    )

    op.add_column(
        "analytics_events",
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_events_campaign_id",
        "analytics_events",
        "campaigns",
        ["campaign_id"],
        ["id"],
    )

    op.create_index(
        "ix_events_campaign_created_at",
        "analytics_events",
        ["campaign_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_events_campaign_created_at",
        table_name="analytics_events",
    )

    op.drop_constraint(
        "fk_events_campaign_id",
        "analytics_events",
        type_="foreignkey",
    )

    op.drop_column(
        "analytics_events",
        "campaign_id",
    )

    op.drop_table("campaigns")
