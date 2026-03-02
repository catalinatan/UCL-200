from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from api.database import get_db
from api.models import Answer, Location, Session
from api.schemas import AnswerRequest, AnswerResponse, GameState, SessionCreate, SessionStats

router = APIRouter(prefix="/sessions")

GAME_DURATION = 90  # seconds


def _remaining_seconds(session: Session) -> int:
    if not session.started_at:
        return GAME_DURATION
    elapsed = (datetime.utcnow() - session.started_at).total_seconds()
    return max(0, int(GAME_DURATION - elapsed))


def _is_over(session: Session, total_locations: int, db: DBSession) -> bool:
    if _remaining_seconds(session) <= 0:
        return True
    answered_count = db.query(Answer).filter(Answer.session_id == session.id).count()
    return answered_count >= total_locations


@router.post("", response_model=SessionCreate, status_code=201)
def create_session(db: DBSession = Depends(get_db)):
    from api.models import Location as Loc
    total = db.query(Loc).count()
    session = Session(id=str(uuid4()))
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionCreate(session_id=session.id, total=total, created_at=session.created_at)


@router.get("/{session_id}", response_model=GameState)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from api.models import Location as Loc
    total = db.query(Loc).count()
    answers = db.query(Answer).filter(Answer.session_id == session_id).all()
    score = sum(1 for a in answers if a.is_correct)
    is_over = _is_over(session, total, db)

    # Persist is_over flag if it just flipped
    if is_over and not session.is_over:
        session.is_over = True
        db.commit()

    return GameState(
        session_id=session.id,
        is_started=session.started_at is not None,
        is_over=is_over,
        remaining_seconds=_remaining_seconds(session),
        score=score,
        total=total,
        answered_location_ids=[a.location_id for a in answers],
    )


@router.post("/{session_id}/answers", response_model=AnswerResponse)
def submit_answer(session_id: str, body: AnswerRequest, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from api.models import Location as Loc
    total = db.query(Loc).count()
    if _is_over(session, total, db):
        raise HTTPException(status_code=400, detail="Game is already over")

    location = db.query(Location).filter(Location.id == body.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    already_answered = (
        db.query(Answer)
        .filter(Answer.session_id == session_id, Answer.location_id == body.location_id)
        .first()
    )
    if already_answered:
        raise HTTPException(status_code=400, detail="Location already answered")

    # Start timer on first answer
    if session.started_at is None:
        session.started_at = datetime.utcnow()

    q = location.question
    is_correct = body.answer.strip() == q.correct_answer.strip()

    answer = Answer(
        session_id=session_id,
        location_id=body.location_id,
        answer_given=body.answer,
        is_correct=is_correct,
        answered_at=datetime.utcnow(),
    )
    db.add(answer)
    db.commit()

    all_answers = db.query(Answer).filter(Answer.session_id == session_id).all()
    score = sum(1 for a in all_answers if a.is_correct)
    is_over = _is_over(session, total, db)

    if is_over and not session.is_over:
        session.is_over = True
        db.commit()

    return AnswerResponse(
        correct=is_correct,
        correct_answer=q.correct_answer,
        score=score,
        total_answered=len(all_answers),
        is_over=is_over,
        remaining_seconds=_remaining_seconds(session),
    )


@router.get("/{session_id}/stats", response_model=SessionStats)
def get_session_stats(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from api.models import Location as Loc
    total = db.query(Loc).count()
    answers = db.query(Answer).filter(Answer.session_id == session_id).all()
    score = sum(1 for a in answers if a.is_correct)
    answered_count = len(answers)
    accuracy = round((score / answered_count * 100) if answered_count > 0 else 0.0, 1)

    elapsed = 0
    if session.started_at:
        elapsed = int((datetime.utcnow() - session.started_at).total_seconds())
        elapsed = min(elapsed, GAME_DURATION)

    return SessionStats(
        session_id=session.id,
        score=score,
        total=total,
        questions_answered=answered_count,
        accuracy_pct=accuracy,
        time_elapsed_seconds=elapsed,
        remaining_seconds=_remaining_seconds(session),
    )
