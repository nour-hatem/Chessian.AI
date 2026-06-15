"""initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-06-15 15:22:35.751216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("lichess_username", sa.String(100), nullable=True),
        sa.Column("chesscom_username", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- games ---
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("pgn", sa.Text, nullable=False),
        sa.Column("moves_hash", sa.String(64), nullable=True),
        sa.Column("white_username", sa.String(100)),
        sa.Column("black_username", sa.String(100)),
        sa.Column("result", sa.String(10)),
        sa.Column("time_control", sa.String(20)),
        sa.Column("opening_eco", sa.String(10)),
        sa.Column("opening_name", sa.String(200)),
        sa.Column("played_at", sa.DateTime),
        sa.Column("clock_data", postgresql.JSON, nullable=True),
        sa.Column("imported_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_games_user_id", "games", ["user_id"])
    op.create_index("ix_games_moves_hash", "games", ["moves_hash"])

    # --- game_analyses ---
    op.create_table(
        "game_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id"), unique=True, nullable=False),
        sa.Column("white_accuracy", sa.Float),
        sa.Column("black_accuracy", sa.Float),
        sa.Column("white_blunders", sa.Integer, server_default="0"),
        sa.Column("white_mistakes", sa.Integer, server_default="0"),
        sa.Column("white_inaccuracies", sa.Integer, server_default="0"),
        sa.Column("black_blunders", sa.Integer, server_default="0"),
        sa.Column("black_mistakes", sa.Integer, server_default="0"),
        sa.Column("black_inaccuracies", sa.Integer, server_default="0"),
        sa.Column("opening_accuracy", sa.Float),
        sa.Column("middlegame_accuracy", sa.Float),
        sa.Column("endgame_accuracy", sa.Float),
        sa.Column("analysis_depth", sa.Integer),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("critical_moments", postgresql.JSON, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    # --- move_analyses ---
    op.create_table(
        "move_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("color", sa.String(5), nullable=False),
        sa.Column("move_uci", sa.String(10)),
        sa.Column("move_san", sa.String(15)),
        sa.Column("fen_before", sa.Text),
        sa.Column("fen_after", sa.Text),
        sa.Column("eval_before", sa.Float),
        sa.Column("eval_after", sa.Float),
        sa.Column("best_move_uci", sa.String(10)),
        sa.Column("best_move_san", sa.String(15)),
        sa.Column("best_line", sa.Text),
        sa.Column("cp_loss", sa.Float),
        sa.Column("classification", sa.String(15)),
        sa.Column("is_critical_moment", sa.Boolean, server_default="false"),
        sa.Column("tactical_motifs", postgresql.JSON, nullable=True),
        sa.Column("time_spent", sa.Float, nullable=True),
    )
    op.create_index("ix_move_analyses_game_id", "move_analyses", ["game_id"])

    # --- move_explanations ---
    op.create_table(
        "move_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "move_analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("move_analyses.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("model_used", sa.String(50)),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table("move_explanations")
    op.drop_table("move_analyses")
    op.drop_table("game_analyses")
    op.drop_table("games")
    op.drop_table("users")
