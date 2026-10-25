"""Pydantic schemas for API request/response models."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Game Schemas ----------

class GameBase(BaseModel):
    source: str
    white_username: Optional[str] = None
    black_username: Optional[str] = None
    result: Optional[str] = None
    time_control: Optional[str] = None
    opening_eco: Optional[str] = None
    opening_name: Optional[str] = None
    played_at: Optional[datetime] = None


class GameCreate(GameBase):
    pgn: str


class GameResponse(GameBase):
    id: uuid.UUID
    imported_at: datetime
    has_analysis: bool = False
    # Raw analysis lifecycle state so the client can tell "never analyzed"
    # (None) apart from pending / processing / complete / failed.
    analysis_status: Optional[str] = None
    # Which side the library owner played, and the result from their point of
    # view ("win" / "loss" / "draw"). None when the side can't be determined.
    user_color: Optional[str] = None
    user_result: Optional[str] = None

    model_config = {"from_attributes": True}


class GameListResponse(BaseModel):
    games: list[GameResponse]
    total: int


# ---------- Import Schemas ----------

class ImportRequest(BaseModel):
    username: str
    max_games: int = Field(default=100, ge=1, le=1000)


class ImportProgress(BaseModel):
    status: str  # importing, complete, failed
    games_imported: int
    total_games: int
    message: str = ""


# ---------- Analysis Schemas ----------

class AnalysisRequest(BaseModel):
    depth: int = 20


class MoveAnalysisResponse(BaseModel):
    move_number: int
    color: str
    move_san: str
    eval_before: Optional[float] = None
    eval_after: Optional[float] = None
    cp_loss: Optional[float] = None
    classification: Optional[str] = None
    best_move_san: Optional[str] = None
    is_critical_moment: bool = False
    explanation: Optional[str] = None
    time_spent: Optional[float] = None

    model_config = {"from_attributes": True}


class GameAnalysisResponse(BaseModel):
    game_id: uuid.UUID
    status: str
    white_accuracy: Optional[float] = None
    black_accuracy: Optional[float] = None
    white_blunders: int = 0
    white_mistakes: int = 0
    white_inaccuracies: int = 0
    black_blunders: int = 0
    black_mistakes: int = 0
    black_inaccuracies: int = 0
    opening_accuracy: Optional[float] = None
    middlegame_accuracy: Optional[float] = None
    endgame_accuracy: Optional[float] = None
    moves: list[MoveAnalysisResponse] = []

    model_config = {"from_attributes": True}


# ---------- Improvement Plan Schemas (D1) ----------

class WeaknessItem(BaseModel):
    id: str
    title: str
    description: str
    severity: str  # "high", "medium", "low"
    expected_gain_elo: int
    dimension: str  # "endgame", "tactics", "opening", "middlegame", "time"
    metric: str


class PlanTask(BaseModel):
    id: str
    title: str
    category: str  # "puzzles", "openings", "endgame", "analysis", "play"
    duration_minutes: int
    description: str
    action_url: str
    action_label: str
    completed: bool = False


class ImprovementPlanResponse(BaseModel):
    user_id: uuid.UUID
    resolved_username: Optional[str] = None
    total_games_analyzed: int
    overall_accuracy: Optional[float] = None
    opening_accuracy: Optional[float] = None
    middlegame_accuracy: Optional[float] = None
    endgame_accuracy: Optional[float] = None
    weakest_phase: str
    blunder_rate_per_game: float
    mistake_rate_per_game: float
    puzzle_rating_center: int
    puzzles_due_count: int
    puzzle_streak: int
    coaching_summary: str
    focus_headline: str
    planned_hours: float
    weaknesses: list[WeaknessItem]
    tasks: list[PlanTask]

