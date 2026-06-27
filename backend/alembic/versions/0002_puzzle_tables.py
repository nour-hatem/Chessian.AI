"""puzzle_tables

Revision ID: 0002
Revises: 0001

Adds two new tables — puzzles and puzzle_attempts — that are fully independent
of the existing game/analysis tables. No locks on existing tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create puzzles and puzzle_attempts tables."""

    # --- puzzles ---
    op.create_table(
        "puzzles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lichess_id", sa.String(20), unique=True, nullable=False),
        sa.Column("fen", sa.Text, nullable=False),
        sa.Column("moves", sa.Text, nullable=False),
        sa.Column("themes", postgresql.JSON, nullable=True),
        sa.Column("opening_tags", postgresql.JSON, nullable=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("rating_deviation", sa.Integer, server_default="500"),
        sa.Column("popularity", sa.Integer, server_default="0"),
        sa.Column("nb_plays", sa.Integer, server_default="0"),
        sa.Column("game_url", sa.String(200), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_puzzles_lichess_id", "puzzles", ["lichess_id"], unique=True)
    op.create_index("ix_puzzles_rating", "puzzles", ["rating"])

    # --- puzzle_attempts ---
    op.create_table(
        "puzzle_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "puzzle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("puzzles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SM-2 state
        sa.Column("easiness", sa.Float, server_default="2.5"),
        sa.Column("interval", sa.Integer, server_default="1"),
        sa.Column("repetitions", sa.Integer, server_default="0"),
        sa.Column("next_due_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Tracking
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_quality", sa.Integer, nullable=True),
        sa.Column("total_attempts", sa.Integer, server_default="0"),
        sa.Column("total_correct", sa.Integer, server_default="0"),
    )
    op.create_index("ix_puzzle_attempts_user_id", "puzzle_attempts", ["user_id"])
    op.create_index("ix_puzzle_attempts_puzzle_id", "puzzle_attempts", ["puzzle_id"])
    # Composite unique: one SM-2 record per user per puzzle
    op.create_index(
        "uq_puzzle_attempts_user_puzzle",
        "puzzle_attempts",
        ["user_id", "puzzle_id"],
        unique=True,
    )
    # Index for the SM-2 scheduling query: find all overdue attempts for a user
    op.create_index(
        "ix_puzzle_attempts_user_due",
        "puzzle_attempts",
        ["user_id", "next_due_date"],
    )


def downgrade() -> None:
    """Drop puzzle tables in reverse FK order."""
    op.drop_index("ix_puzzle_attempts_user_due", table_name="puzzle_attempts")
    op.drop_index("uq_puzzle_attempts_user_puzzle", table_name="puzzle_attempts")
    op.drop_index("ix_puzzle_attempts_puzzle_id", table_name="puzzle_attempts")
    op.drop_index("ix_puzzle_attempts_user_id", table_name="puzzle_attempts")
    op.drop_table("puzzle_attempts")
    op.drop_index("ix_puzzles_rating", table_name="puzzles")
    op.drop_index("ix_puzzles_lichess_id", table_name="puzzles")
    op.drop_table("puzzles")
