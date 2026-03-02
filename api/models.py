from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from api.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    img_path = Column(String, nullable=False)

    question = relationship("Question", back_populates="location", uselist=False)
    answers = relationship("Answer", back_populates="location")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, unique=True)
    text = Column(String, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)

    location = relationship("Location", back_populates="question")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # set on first answer
    is_over = Column(Boolean, default=False, nullable=False)

    answers = relationship("Answer", back_populates="session")
    leaderboard_entry = relationship("LeaderboardEntry", back_populates="session", uselist=False)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    answer_given = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="answers")
    location = relationship("Location", back_populates="answers")


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, nullable=False)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True)
    score = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="leaderboard_entry")
