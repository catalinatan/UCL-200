from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --------------------------------------------------------------------------- #
# Locations                                                                   #
# --------------------------------------------------------------------------- #

class LocationBase(BaseModel):
    id: int
    key: str
    lat: float
    lng: float
    img_path: str

    model_config = {"from_attributes": True}


class QuestionOut(BaseModel):
    id: int
    location_id: int
    location_key: str
    question: str
    options: list[str]  # shuffled; correct answer included but not flagged

    model_config = {"from_attributes": True}


class LocationDetail(LocationBase):
    question: QuestionOut


# --------------------------------------------------------------------------- #
# Sessions                                                                    #
# --------------------------------------------------------------------------- #

class SessionCreate(BaseModel):
    session_id: str
    total: int
    created_at: datetime


class GameState(BaseModel):
    session_id: str
    is_started: bool
    is_over: bool
    remaining_seconds: int
    score: int
    total: int
    answered_location_ids: list[int]


class SessionStats(BaseModel):
    session_id: str
    score: int
    total: int
    questions_answered: int
    accuracy_pct: float
    time_elapsed_seconds: int
    remaining_seconds: int


# --------------------------------------------------------------------------- #
# Answers                                                                     #
# --------------------------------------------------------------------------- #

class AnswerRequest(BaseModel):
    location_id: int
    answer: str


class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    score: int
    total_answered: int
    is_over: bool
    remaining_seconds: int


# --------------------------------------------------------------------------- #
# Leaderboard                                                                 #
# --------------------------------------------------------------------------- #

class LeaderboardSubmit(BaseModel):
    player_name: str
    session_id: str


class LeaderboardEntry(BaseModel):
    id: int
    rank: int
    player_name: str
    score: int
    total: int
    accuracy_pct: float
    completed_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardSubmitResponse(BaseModel):
    id: int
    player_name: str
    score: int
    rank: int
