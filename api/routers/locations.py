import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Location
from api.schemas import LocationBase, LocationDetail, QuestionOut

router = APIRouter(prefix="/locations")


@router.get("", response_model=list[LocationBase])
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).order_by(Location.id).all()


@router.get("/{location_id}", response_model=LocationDetail)
def get_location(location_id: int, db: Session = Depends(get_db)):
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    q = loc.question
    all_options = [q.option_a, q.option_b, q.option_c, q.correct_answer]
    shuffled = random.sample(all_options, len(all_options))

    question_out = QuestionOut(
        id=q.id,
        location_id=loc.id,
        location_key=loc.key,
        question=q.text,
        options=shuffled,
    )
    return LocationDetail(
        id=loc.id,
        key=loc.key,
        lat=loc.lat,
        lng=loc.lng,
        img_path=loc.img_path,
        question=question_out,
    )
