import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Question
from api.schemas import QuestionOut

router = APIRouter(prefix="/questions")


def _build_question_out(q: Question) -> QuestionOut:
    all_options = [q.option_a, q.option_b, q.option_c, q.correct_answer]
    shuffled = random.sample(all_options, len(all_options))
    return QuestionOut(
        id=q.id,
        location_id=q.location_id,
        location_key=q.location.key,
        question=q.text,
        options=shuffled,
    )


@router.get("", response_model=QuestionOut)
def get_question_by_location(
    location_id: int = Query(..., description="Location ID to fetch the question for"),
    db: Session = Depends(get_db),
):
    q = db.query(Question).filter(Question.location_id == location_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found for this location")
    return _build_question_out(q)


@router.get("/{question_id}", response_model=QuestionOut)
def get_question_by_id(question_id: int, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return _build_question_out(q)
