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
