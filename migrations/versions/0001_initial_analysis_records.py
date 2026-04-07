"""Initial analysis_records table

Revision ID: 0001
Revises:
Create Date: 2026-04-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("amendment_filename", sa.String(), nullable=False),
        sa.Column("result", postgresql.JSON(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analysis_records")
