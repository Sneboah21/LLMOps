"""Add session display_name

Revision ID: b7c8a1f0d2e3
Revises: 9a358738047f
Create Date: 2026-07-09 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c8a1f0d2e3"
down_revision: Union[str, Sequence[str], None] = "9a358738047f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("display_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "display_name")
