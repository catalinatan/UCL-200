"""
Streamlit entry point for UCL Guessr.

Self-contained: imports the DB layer directly instead of talking to a
FastAPI backend over HTTP. This lets the app run on Streamlit Community
Cloud as a single process.
"""
import os
import random
import time
from datetime import datetime
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy.orm import Session as DBSession

from api.database import SessionLocal
from api.models import Answer, LeaderboardEntry, Location, Question
from api.models import Session as GameSession
from api.seed import seed

GAME_DURATION = 90  # seconds


# ---------------------------------------------------------------------------
# One-time DB seed on cold start
# ---------------------------------------------------------------------------
@st.cache_resource
def _init_db():
    seed()
    return True


_init_db()


# ---------------------------------------------------------------------------
# In-process "API" — mirrors the FastAPI routes but operates on the DB directly
# ---------------------------------------------------------------------------

def _remaining_seconds(session: GameSession) -> int:
    if not session.started_at:
        return GAME_DURATION
    elapsed = (datetime.utcnow() - session.started_at).total_seconds()
    return max(0, int(GAME_DURATION - elapsed))


def _is_over(session: GameSession, total_locations: int, db: DBSession) -> bool:
    if _remaining_seconds(session) <= 0:
        return True
    answered_count = db.query(Answer).filter(Answer.session_id == session.id).count()
    return answered_count >= total_locations


def new_game() -> str:
    db = SessionLocal()
    try:
        session = GameSession(id=str(uuid4()))
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def get_game_state(session_id: str) -> dict:
    db = SessionLocal()
    try:
        session = db.query(GameSession).filter(GameSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        total = db.query(Location).count()
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        score = sum(1 for a in answers if a.is_correct)
        is_over = _is_over(session, total, db)
        if is_over and not session.is_over:
            session.is_over = True
            db.commit()
        return {
            "session_id": session.id,
            "is_started": session.started_at is not None,
            "is_over": is_over,
            "remaining_seconds": _remaining_seconds(session),
            "score": score,
            "total": total,
            "answered_location_ids": [a.location_id for a in answers],
        }
    finally:
        db.close()


@st.cache_data
def get_locations() -> list[dict]:
    db = SessionLocal()
    try:
        rows = db.query(Location).order_by(Location.id).all()
        return [
            {"id": loc.id, "key": loc.key, "lat": loc.lat, "lng": loc.lng, "img_path": loc.img_path}
            for loc in rows
        ]
    finally:
        db.close()


def get_question(location_id: int) -> dict:
    db = SessionLocal()
    try:
        q = db.query(Question).filter(Question.location_id == location_id).first()
        if not q:
            raise ValueError("Question not found for this location")
        all_options = [q.option_a, q.option_b, q.option_c, q.correct_answer]
        shuffled = random.sample(all_options, len(all_options))
        return {
            "id": q.id,
            "location_id": q.location_id,
            "location_key": q.location.key,
            "question": q.text,
            "options": shuffled,
        }
    finally:
        db.close()


def submit_answer(session_id: str, location_id: int, answer_text: str) -> dict:
    db = SessionLocal()
    try:
        session = db.query(GameSession).filter(GameSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")

        total = db.query(Location).count()
        if _is_over(session, total, db):
            raise ValueError("Game is already over")

        location = db.query(Location).filter(Location.id == location_id).first()
        if not location:
            raise ValueError("Location not found")

        already = (
            db.query(Answer)
            .filter(Answer.session_id == session_id, Answer.location_id == location_id)
            .first()
        )
        if already:
            raise ValueError("Location already answered")

        if session.started_at is None:
            session.started_at = datetime.utcnow()

        q = location.question
        is_correct = answer_text.strip() == q.correct_answer.strip()

        db.add(
            Answer(
                session_id=session_id,
                location_id=location_id,
                answer_given=answer_text,
                is_correct=is_correct,
                answered_at=datetime.utcnow(),
            )
        )
        db.commit()

        all_answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        score = sum(1 for a in all_answers if a.is_correct)
        is_over = _is_over(session, total, db)
        if is_over and not session.is_over:
            session.is_over = True
            db.commit()

        return {
            "correct": is_correct,
            "correct_answer": q.correct_answer,
            "score": score,
            "total_answered": len(all_answers),
            "is_over": is_over,
            "remaining_seconds": _remaining_seconds(session),
        }
    finally:
        db.close()


def submit_leaderboard(player_name: str, session_id: str) -> dict:
    db = SessionLocal()
    try:
        session = db.query(GameSession).filter(GameSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        if not session.is_over:
            raise ValueError("Game must be finished before submitting to leaderboard")

        existing = (
            db.query(LeaderboardEntry)
            .filter(LeaderboardEntry.session_id == session_id)
            .first()
        )
        if existing:
            rank = _compute_rank(db, existing)
            return {"id": existing.id, "player_name": existing.player_name, "score": existing.score, "rank": rank}

        total = db.query(Location).count()
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        score = sum(1 for a in answers if a.is_correct)

        entry = LeaderboardEntry(
            player_name=player_name.strip(),
            session_id=session_id,
            score=score,
            total=total,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        rank = _compute_rank(db, entry)
        return {"id": entry.id, "player_name": entry.player_name, "score": score, "rank": rank}
    finally:
        db.close()


def _compute_rank(db: DBSession, entry: LeaderboardEntry) -> int:
    ahead = (
        db.query(LeaderboardEntry)
        .filter(
            (LeaderboardEntry.score > entry.score)
            | (
                (LeaderboardEntry.score == entry.score)
                & (LeaderboardEntry.completed_at < entry.completed_at)
            )
        )
        .count()
    )
    return ahead + 1


def get_leaderboard(limit: int = 5) -> list[dict]:
    db = SessionLocal()
    try:
        entries = (
            db.query(LeaderboardEntry)
            .order_by(LeaderboardEntry.score.desc(), LeaderboardEntry.completed_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "rank": idx + 1,
                "player_name": e.player_name,
                "score": e.score,
                "total": e.total,
                "accuracy_pct": round(e.score / e.total * 100, 1) if e.total > 0 else 0.0,
            }
            for idx, e in enumerate(entries)
        ]
    finally:
        db.close()


def build_map_html(selected_key: str = "") -> str:
    locations = get_locations()
    markers = []
    center_lat, center_lng, zoom = 51.52467, -0.13439, 14

    for loc in locations:
        is_selected = loc["key"] == selected_key
        if is_selected:
            center_lat, center_lng, zoom = loc["lat"], loc["lng"], 16

        color = "#e74c3c" if is_selected else "#3388ff"
        size = 22 if is_selected else 14
        border = "3px solid white" if is_selected else "2px solid white"
        star = " &#11088;" if is_selected else ""
        trivia_note = (
            "Currently selected for trivia" if is_selected else "Use the dropdown to select for trivia"
        )

        icon = (
            f"L.divIcon({{"
            f"html: '<div style=\"background:{color};width:{size}px;height:{size}px;"
            f"border-radius:50%;border:{border};box-shadow:0 0 6px rgba(0,0,0,0.5)\"></div>',"
            f"iconSize: [{size}, {size}],"
            f"iconAnchor: [{size // 2}, {size // 2}],"
            f"popupAnchor: [0, -{size // 2}],"
            f"className: ''"
            f"}})"
        )
        popup = (
            f"<div style='width:200px;font-family:Arial,sans-serif;'>"
            f"<h4 style='color:#003366;margin:0 0 8px;'>{loc['key']}{star}</h4>"
            f"<p style='margin:0;font-size:0.85em;color:#555;'>{trivia_note}</p>"
            f"</div>"
        )
        markers.append(
            f"L.marker([{loc['lat']}, {loc['lng']}], {{icon: {icon}}})"
            f".bindPopup(`{popup}`).addTo(map);"
        )

    markers_js = "\n".join(markers)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    body {{ margin: 0; padding: 0; }}
    #map {{ width: 100%; height: 100vh; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([{center_lat}, {center_lng}], {zoom});
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }}).addTo(map);
    {markers_js}
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "selected_location_id" not in st.session_state:
    st.session_state.selected_location_id = None
if "show_splash" not in st.session_state:
    st.session_state.show_splash = True
if "splash_start_time" not in st.session_state:
    st.session_state.splash_start_time = time.time()
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "leaderboard_submitted" not in st.session_state:
    st.session_state.leaderboard_submitted = False


# ---------------------------------------------------------------------------
# Splash (2s)
# ---------------------------------------------------------------------------
if st.session_state.show_splash:
    elapsed = time.time() - st.session_state.splash_start_time
    if elapsed < 2.0:
        st.markdown(
            """
            <style>
                .main .block-container { padding: 0; }
                header[data-testid="stHeader"] { display: none; }
            </style>
            <div style="
                position: fixed; top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex; justify-content: center; align-items: center;
                z-index: 9999;
            ">
                <div style="text-align: center; color: white;">
                    <h1 style="font-size: 5em; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                        UCL Guessr
                    </h1>
                    <p style="font-size: 2em; opacity: 0.9;">Interactive Campus Trivia Game</p>
                    <div style="
                        width: 80px; height: 80px; margin: 50px auto 0;
                        border: 6px solid rgba(255,255,255,0.3);
                        border-top: 6px solid white;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                    "></div>
                    <p style="font-size: 1.2em; margin-top: 30px; opacity: 0.7;">Loading...</p>
                </div>
            </div>
            <style>
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(0.1)
        st.rerun()
    else:
        st.session_state.show_splash = False
        st.rerun()
    st.stop()


# ---------------------------------------------------------------------------
# Initialise game session on first render
# ---------------------------------------------------------------------------
if st.session_state.session_id is None:
    st.session_state.session_id = new_game()

session_id = st.session_state.session_id
game_state = get_game_state(session_id)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
logo_path = "src/images/logo.png"
if os.path.exists(logo_path):
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        st.image(logo_path, width=60)
    with col_title:
        st.markdown("<h1 style='margin:0; font-size:3rem;'>UCL Guessr</h1>", unsafe_allow_html=True)
else:
    st.markdown("<h1 style='font-size:3rem;'>UCL Guessr</h1>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Game over screen
# ---------------------------------------------------------------------------
if game_state["is_over"]:
    score = game_state["score"]
    total = game_state["total"]

    st.error("GAME OVER!")

    _, col_card, _ = st.columns([1, 2, 1])
    with col_card:
        if score >= 8:
            message = "Excellent!"
        elif score >= 6:
            message = "Good job!"
        else:
            message = "Keep studying!"

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px; border-radius: 15px; text-align: center; color: white;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            ">
                <h2 style="margin: 0; font-size: 2.5em;">Final Score</h2>
                <h1 style="margin: 20px 0; font-size: 4em; font-weight: bold;">{score}/{total}</h1>
                <p style="font-size: 1.2em;">{message}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        if not st.session_state.leaderboard_submitted:
            st.subheader("Submit to Leaderboard")
            player_name = st.text_input("Your name:", max_chars=30, key="player_name_input")
            if st.button("Submit Score", use_container_width=True) and player_name.strip():
                result = submit_leaderboard(player_name.strip(), session_id)
                st.session_state.leaderboard_submitted = True
                st.success(f"Submitted! You're ranked #{result['rank']} on the leaderboard.")
                st.rerun()
        else:
            st.success("Score submitted to leaderboard!")

        st.subheader("Top 5")
        top_entries = get_leaderboard(limit=5)
        if top_entries:
            for entry in top_entries:
                medals = {1: "1st", 2: "2nd", 3: "3rd"}
                rank_label = medals.get(entry["rank"], f"#{entry['rank']}")
                st.markdown(
                    f"**{rank_label}** — **{entry['player_name']}** — "
                    f"{entry['score']}/{entry['total']} ({entry['accuracy_pct']}%)"
                )
        else:
            st.info("No scores yet — be the first!")

    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("Play Again", use_container_width=True):
            st.session_state.session_id = new_game()
            st.session_state.selected_location_id = None
            st.session_state.current_question = None
            st.session_state.leaderboard_submitted = False
            st.session_state.show_splash = True
            st.session_state.splash_start_time = time.time()
            st.rerun()
    st.stop()


# ---------------------------------------------------------------------------
# Timer & score bar
# ---------------------------------------------------------------------------
st.markdown("---")
col_timer, col_score, col_progress, col_refresh = st.columns([2, 1, 1, 1])

with col_timer:
    remaining = game_state["remaining_seconds"]
    if game_state["is_started"]:
        mins, secs = divmod(remaining, 60)
        if remaining <= 0:
            st.error("TIME'S UP!")
        elif remaining <= 30:
            st.markdown(f"**Time:** {mins:02d}:{secs:02d}")
        elif remaining <= 60:
            st.markdown(f"**Time:** {mins:02d}:{secs:02d}")
        else:
            st.markdown(f"**Time:** {mins:02d}:{secs:02d}")
    else:
        st.info("Timer: Ready")

with col_score:
    st.metric("Score", f"{game_state['score']}/{len(game_state['answered_location_ids'])}")

with col_progress:
    st.metric("Progress", f"{len(game_state['answered_location_ids'])}/{game_state['total']}")

with col_refresh:
    if st.button("Refresh"):
        st.rerun()


# ---------------------------------------------------------------------------
# Map + trivia panel
# ---------------------------------------------------------------------------
locations = get_locations()
id_to_loc = {loc["id"]: loc for loc in locations}
key_to_id = {loc["key"]: loc["id"] for loc in locations}

col_map, col_trivia = st.columns([2, 1])

with col_map:
    st.subheader("Map")
    selected_key = ""
    if st.session_state.selected_location_id:
        loc = id_to_loc.get(st.session_state.selected_location_id)
        selected_key = loc["key"] if loc else ""
    components.html(build_map_html(selected_key), height=500)

with col_trivia:
    st.subheader("Trivia")

    dropdown_options = [""] + [loc["key"] for loc in locations]
    current_key = ""
    if st.session_state.selected_location_id:
        loc = id_to_loc.get(st.session_state.selected_location_id)
        current_key = loc["key"] if loc else ""

    current_index = dropdown_options.index(current_key) if current_key in dropdown_options else 0

    selected_key = st.selectbox(
        "Select a location for trivia:",
        dropdown_options,
        index=current_index,
        key="location_dropdown",
    )

    new_id = key_to_id.get(selected_key) if selected_key else None
    if new_id != st.session_state.selected_location_id:
        st.session_state.selected_location_id = new_id
        st.session_state.current_question = None
        st.rerun()

    if not st.session_state.selected_location_id:
        st.info("Select a location from the dropdown to start the trivia!")
    else:
        location_id = st.session_state.selected_location_id
        already_answered = location_id in game_state["answered_location_ids"]

        loc_data = id_to_loc.get(location_id)
        if loc_data:
            img_path = loc_data["img_path"]
            if os.path.exists(img_path):
                st.image(img_path, width=300)

        if already_answered:
            st.info("You've already answered this one. Select another building!")
            if st.button("Try Another Location"):
                st.session_state.selected_location_id = None
                st.session_state.current_question = None
                st.rerun()
        else:
            if (
                st.session_state.current_question is None
                or st.session_state.current_question["location_id"] != location_id
            ):
                st.session_state.current_question = get_question(location_id)

            q = st.session_state.current_question
            st.write(f"**{q['question']}**")
            st.write("Choose your answer:")

            col_a, col_b = st.columns(2)
            options = q["options"]

            def make_answer_handler(opt):
                result = submit_answer(session_id, location_id, opt)
                if result["correct"]:
                    st.success("Correct!")
                else:
                    st.error(f"Incorrect. Answer: {result['correct_answer']}")
                st.session_state.current_question = None
                st.rerun()

            with col_a:
                if len(options) > 0 and st.button(f"A) {options[0]}", key=f"opt0_{location_id}"):
                    make_answer_handler(options[0])
                if len(options) > 2 and st.button(f"C) {options[2]}", key=f"opt2_{location_id}"):
                    make_answer_handler(options[2])

            with col_b:
                if len(options) > 1 and st.button(f"B) {options[1]}", key=f"opt1_{location_id}"):
                    make_answer_handler(options[1])
                if len(options) > 3 and st.button(f"D) {options[3]}", key=f"opt3_{location_id}"):
                    make_answer_handler(options[3])
