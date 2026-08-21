"""Add deterministic bootstrap keys and normalized frequency rank.

Revision ID: p02_0002_bootstrap_keys
Revises: p01_0001_initial
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p02_0002_bootstrap_keys"
down_revision: str | None = "p01_0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("WordBook", sa.Column("frqRank", sa.Integer(), nullable=True))
    op.drop_index("WordBook_word_idx", table_name="WordBook")
    op.create_index("WordBook_word_key", "WordBook", ["word"], unique=True)
    op.create_index(
        "WordBook_frqRank_word_id_idx",
        "WordBook",
        ["frqRank", "word", "id"],
        unique=False,
    )
    op.create_index("Course_value_key", "Course", ["value"], unique=True)


def downgrade() -> None:
    op.drop_index("Course_value_key", table_name="Course")
    op.drop_index("WordBook_frqRank_word_id_idx", table_name="WordBook")
    op.drop_index("WordBook_word_key", table_name="WordBook")
    op.create_index("WordBook_word_idx", "WordBook", ["word"], unique=False)
    op.drop_column("WordBook", "frqRank")
