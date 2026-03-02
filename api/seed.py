"""
Seed the SQLite database with UCL campus locations and trivia questions.
Safe to call multiple times — no-op if data already exists.
"""
from api.database import Base, SessionLocal, engine
from api.models import Location, Question
from api.data.locations import LOCATIONS


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Location).count() > 0:
            return  # already seeded
        for loc_data in LOCATIONS:
            location = Location(
                key=loc_data["key"],
                lat=loc_data["lat"],
                lng=loc_data["lng"],
                img_path=loc_data["img_path"],
            )
            db.add(location)
            db.flush()  # get location.id

            question = Question(
                location_id=location.id,
                text=loc_data["question"],
                option_a=loc_data["options"][0],
                option_b=loc_data["options"][1],
                option_c=loc_data["options"][2],
                correct_answer=loc_data["answer"],
            )
            db.add(question)

        db.commit()
        print(f"Seeded {len(LOCATIONS)} locations.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Done.")
