import os
import time

import requests
import streamlit as st
import streamlit.components.v1 as components

BACKEND = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "selected_location_id" not in st.session_state:
    st.session_state.selected_location_id = None  # int or None
if "show_splash" not in st.session_state:
    st.session_state.show_splash = True
if "splash_start_time" not in st.session_state:
    st.session_state.splash_start_time = time.time()
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "leaderboard_submitted" not in st.session_state:
    st.session_state.leaderboard_submitted = False


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def new_game() -> str:
    resp = requests.post(f"{BACKEND}/sessions")
    resp.raise_for_status()
    return resp.json()["session_id"]


def get_game_state(session_id: str) -> dict:
    resp = requests.get(f"{BACKEND}/sessions/{session_id}")
    resp.raise_for_status()
    return resp.json()


def get_locations() -> list[dict]:
    resp = requests.get(f"{BACKEND}/locations")
    resp.raise_for_status()
    return resp.json()


def get_question(location_id: int) -> dict:
    resp = requests.get(f"{BACKEND}/questions", params={"location_id": location_id})
    resp.raise_for_status()
    return resp.json()


def submit_answer(session_id: str, location_id: int, answer: str) -> dict:
    resp = requests.post(
        f"{BACKEND}/sessions/{session_id}/answers",
        json={"location_id": location_id, "answer": answer},
    )
    resp.raise_for_status()
    return resp.json()


def submit_leaderboard(player_name: str, session_id: str) -> dict:
    resp = requests.post(
        f"{BACKEND}/leaderboard",
        json={"player_name": player_name, "session_id": session_id},
    )
    resp.raise_for_status()
    return resp.json()


def get_leaderboard(limit: int = 5) -> list[dict]:
    resp = requests.get(f"{BACKEND}/leaderboard", params={"limit": limit})
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Splash screen (2 seconds)
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
# Initialise backend session on first real render
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

    st.error("⏰ GAME OVER!")

    _, col_card, _ = st.columns([1, 2, 1])
    with col_card:
        if score >= 8:
            message = "🏆 Excellent!"
        elif score >= 6:
            message = "👍 Good job!"
        else:
            message = "📚 Keep studying!"

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px; border-radius: 15px; text-align: center; color: white;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            ">
                <h2 style="margin: 0; font-size: 2.5em;">🎯 Final Score</h2>
                <h1 style="margin: 20px 0; font-size: 4em; font-weight: bold;">{score}/{total}</h1>
                <p style="font-size: 1.2em;">{message}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Leaderboard submission
        st.markdown("---")
        if not st.session_state.leaderboard_submitted:
            st.subheader("🏅 Submit to Leaderboard")
            player_name = st.text_input("Your name:", max_chars=30, key="player_name_input")
            if st.button("Submit Score", use_container_width=True) and player_name.strip():
                result = submit_leaderboard(player_name.strip(), session_id)
                st.session_state.leaderboard_submitted = True
                st.success(f"Submitted! You're ranked #{result['rank']} on the leaderboard.")
                st.rerun()
        else:
            st.success("Score submitted to leaderboard!")

        # Top 5 leaderboard
        st.subheader("🏆 Top 5")
        top_entries = get_leaderboard(limit=5)
        if top_entries:
            for entry in top_entries:
                medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                medal = medals.get(entry["rank"], f"#{entry['rank']}")
                st.markdown(
                    f"{medal} **{entry['player_name']}** — "
                    f"{entry['score']}/{entry['total']} ({entry['accuracy_pct']}%)"
                )
        else:
            st.info("No scores yet — be the first!")

    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("🔄 Play Again", use_container_width=True):
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
            st.error("⏰ TIME'S UP!")
        elif remaining <= 30:
            st.markdown(f"🔴 **Time:** {mins:02d}:{secs:02d}")
        elif remaining <= 60:
            st.markdown(f"🟠 **Time:** {mins:02d}:{secs:02d}")
        else:
            st.markdown(f"🟢 **Time:** {mins:02d}:{secs:02d}")
    else:
        st.info("⏱️ Timer: Ready")

with col_score:
    st.metric("Score", f"{game_state['score']}/{len(game_state['answered_location_ids'])}")

with col_progress:
    st.metric("Progress", f"{len(game_state['answered_location_ids'])}/{game_state['total']}")

with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

# ---------------------------------------------------------------------------
# Map + trivia panel
# ---------------------------------------------------------------------------
locations = get_locations()
# Build lookup maps: id → location dict, key → id
id_to_loc = {loc["id"]: loc for loc in locations}
key_to_id = {loc["key"]: loc["id"] for loc in locations}

col_map, col_trivia = st.columns([2, 1])

with col_map:
    st.subheader("Map")
    selected_key = ""
    if st.session_state.selected_location_id:
        loc = id_to_loc.get(st.session_state.selected_location_id)
        selected_key = loc["key"] if loc else ""
    map_url = f"{BACKEND}/map?selected={requests.utils.quote(selected_key)}"
    map_html = requests.get(map_url).text
    components.html(map_html, height=500)

with col_trivia:
    st.subheader("Trivia")

    # Dropdown shows human-readable keys; internally we track by ID
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

    # Update selected_location_id when dropdown changes
    new_id = key_to_id.get(selected_key) if selected_key else None
    if new_id != st.session_state.selected_location_id:
        st.session_state.selected_location_id = new_id
        st.session_state.current_question = None
        st.rerun()

    if not st.session_state.selected_location_id:
        st.info("👆 Select a location from the dropdown to start the trivia!")
    else:
        location_id = st.session_state.selected_location_id
        already_answered = location_id in game_state["answered_location_ids"]

        loc_data = id_to_loc.get(location_id)
        if loc_data:
            img_path = loc_data["img_path"]
            if os.path.exists(img_path):
                st.image(img_path, width=300)

        if already_answered:
            st.info("✅ You've already answered this one. Select another building!")
            if st.button("Try Another Location"):
                st.session_state.selected_location_id = None
                st.session_state.current_question = None
                st.rerun()
        else:
            # Cache question to avoid reshuffling on every rerun
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
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Answer: {result['correct_answer']}")
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
