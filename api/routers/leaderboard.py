from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from api.database import get_db
from api.models import Answer, LeaderboardEntry, Session
from api.schemas import LeaderboardEntry as LeaderboardEntrySchema
from api.schemas import LeaderboardSubmit, LeaderboardSubmitResponse

router = APIRouter(prefix="/leaderboard")


@router.get("", response_model=list[LeaderboardEntrySchema])
def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    db: DBSession = Depends(get_db),
):
    entries = (
        db.query(LeaderboardEntry)
        .order_by(LeaderboardEntry.score.desc(), LeaderboardEntry.completed_at.asc())
        .limit(limit)
        .all()
    )
    return [
        LeaderboardEntrySchema(
            id=e.id,
            rank=idx + 1,
            player_name=e.player_name,
            score=e.score,
            total=e.total,
            accuracy_pct=round(e.score / e.total * 100, 1) if e.total > 0 else 0.0,
            completed_at=e.completed_at,
        )
        for idx, e in enumerate(entries)
    ]


@router.post("", response_model=LeaderboardSubmitResponse, status_code=201)
def submit_to_leaderboard(body: LeaderboardSubmit, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == body.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_over:
        raise HTTPException(status_code=400, detail="Game must be finished before submitting to leaderboard")

    # Prevent duplicate submissions for the same session
    existing = db.query(LeaderboardEntry).filter(LeaderboardEntry.session_id == body.session_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Score already submitted for this session")

    from api.models import Location as Loc
    total = db.query(Loc).count()
    answers = db.query(Answer).filter(Answer.session_id == body.session_id).all()
    score = sum(1 for a in answers if a.is_correct)

    entry = LeaderboardEntry(
        player_name=body.player_name.strip(),
        session_id=body.session_id,
        score=score,
        total=total,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    rank_count = (
        db.query(LeaderboardEntry)
        .filter(
            (LeaderboardEntry.score > score)
            | ((LeaderboardEntry.score == score) & (LeaderboardEntry.completed_at < entry.completed_at))
        )
        .count()
    )

    return LeaderboardSubmitResponse(
        id=entry.id,
        player_name=entry.player_name,
        score=score,
        rank=rank_count + 1,
    )
