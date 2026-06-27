"""Database models for Chessian.AI."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base model class."""
    pass


class User(Base):
    """Registered user."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    lichess_username = Column(String(100), nullable=True)
    chesscom_username = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    games = relationship("Game", back_populates="user")
    puzzle_attempts = relationship("PuzzleAttempt", back_populates="user")


class Game(Base):
    """Imported or played chess game."""

    __tablename__ = "games"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(20), nullable=False)  # lichess, chesscom, pgn_upload, platform
    pgn = Column(Text, nullable=False)
    moves_hash = Column(String(64), nullable=True)  # SHA256 for dedup
    white_username = Column(String(100))
    black_username = Column(String(100))
    result = Column(String(10))  # 1-0, 0-1, 1/2-1/2
    time_control = Column(String(20))
    opening_eco = Column(String(10))
    opening_name = Column(String(200))
    played_at = Column(DateTime(timezone=True))
    clock_data = Column(JSON, nullable=True)  # per-move clock times
    imported_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="games")
    analysis = relationship("GameAnalysis", back_populates="game", uselist=False)
    move_analyses = relationship("MoveAnalysis", back_populates="game")


class GameAnalysis(Base):
    """Summary analysis for a complete game."""

    __tablename__ = "game_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), unique=True, nullable=False)
    white_accuracy = Column(Float)
    black_accuracy = Column(Float)
    white_blunders = Column(Integer, default=0)
    white_mistakes = Column(Integer, default=0)
    white_inaccuracies = Column(Integer, default=0)
    black_blunders = Column(Integer, default=0)
    black_mistakes = Column(Integer, default=0)
    black_inaccuracies = Column(Integer, default=0)
    opening_accuracy = Column(Float)
    middlegame_accuracy = Column(Float)
    endgame_accuracy = Column(Float)
    analysis_depth = Column(Integer)
    status = Column(String(20), default="pending")  # pending, processing, complete, failed
    critical_moments = Column(JSON, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    game = relationship("Game", back_populates="analysis")


class MoveAnalysis(Base):
    """Per-move engine analysis data."""

    __tablename__ = "move_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    move_number = Column(Integer, nullable=False)
    color = Column(String(5), nullable=False)  # white / black
    move_uci = Column(String(10))
    move_san = Column(String(15))
    fen_before = Column(Text)
    fen_after = Column(Text)
    eval_before = Column(Float)  # centipawns
    eval_after = Column(Float)
    best_move_uci = Column(String(10))
    best_move_san = Column(String(15))
    best_line = Column(Text)  # PV as space-separated UCI
    cp_loss = Column(Float)
    classification = Column(String(15))  # brilliant, best, good, inaccuracy, mistake, blunder
    is_critical_moment = Column(Boolean, default=False)
    tactical_motifs = Column(JSON, nullable=True)  # list of detected motifs
    time_spent = Column(Float, nullable=True)  # seconds spent on this move

    game = relationship("Game", back_populates="move_analyses")
    explanation = relationship("MoveExplanation", back_populates="move_analysis", uselist=False)


class MoveExplanation(Base):
    """LLM-generated natural language explanation for a move."""

    __tablename__ = "move_explanations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    move_analysis_id = Column(
        UUID(as_uuid=True), ForeignKey("move_analyses.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    explanation = Column(Text, nullable=False)
    model_used = Column(String(50))
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    move_analysis = relationship("MoveAnalysis", back_populates="explanation")


class Puzzle(Base):
    """A single tactical puzzle sourced from Lichess."""

    __tablename__ = "puzzles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lichess_id = Column(String(20), unique=True, nullable=False, index=True)
    # FEN of the position *before* the first puzzle move (opponent's last move
    # has already been played; it is the user's turn to find the winning move).
    fen = Column(Text, nullable=False)
    # Space-separated UCI moves forming the full solution line, e.g.
    # "e2e4 e7e5 d1h5" — the first move is the opponent's "setup" move; the
    # user must play the second move (index 1), then the engine replies, etc.
    moves = Column(Text, nullable=False)
    themes = Column(JSON, nullable=True)         # list[str] e.g. ["fork", "pin"]
    opening_tags = Column(JSON, nullable=True)   # list[str] e.g. ["sicilianDefense"]
    rating = Column(Integer, nullable=False, index=True)
    rating_deviation = Column(Integer, default=500)
    popularity = Column(Integer, default=0)
    nb_plays = Column(Integer, default=0)
    game_url = Column(String(200), nullable=True)
    imported_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    attempts = relationship("PuzzleAttempt", back_populates="puzzle")


class PuzzleAttempt(Base):
    """SM-2 spaced-repetition state for one user × one puzzle."""

    __tablename__ = "puzzle_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("puzzles.id", ondelete="CASCADE"), nullable=False)

    # SM-2 state fields
    easiness = Column(Float, default=2.5)     # E-factor; floor is 1.3
    interval = Column(Integer, default=1)     # days until next review
    repetitions = Column(Integer, default=0)  # consecutive correct answers so far
    next_due_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Tracking
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    last_quality = Column(Integer, nullable=True)  # last SM-2 quality score (0-5)
    total_attempts = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)

    user = relationship("User", back_populates="puzzle_attempts")
    puzzle = relationship("Puzzle", back_populates="attempts")
