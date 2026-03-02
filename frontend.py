import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import os

BACKEND = "http://localhost:3000"

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "selected_location" not in st.session_state:
    st.session_state.selected_location = None
if "show_splash" not in st.session_state:
    st.session_state.show_splash = True
if "splash_start_time" not in st.session_state:
    st.session_state.splash_start_time = time.time()
# Cached per-rerun: question options don't reshuffle on every rerun
if "current_question" not in st.session_state:
    st.session_state.current_question = None


def new_game():
    resp = requests.post(f"{BACKEND}/api/games")
    resp.raise_for_status()
    return resp.json()["session_id"]


def get_game_state(session_id):
    resp = requests.get(f"{BACKEND}/api/games/{session_id}")
    resp.raise_for_status()
    return resp.json()


def get_locations():
    resp = requests.get(f"{BACKEND}/api/locations")
    resp.raise_for_status()
    return resp.json()


def get_question(location_key):
    resp = requests.get(f"{BACKEND}/api/locations/{requests.utils.quote(location_key)}/question")
    resp.raise_for_status()
    return resp.json()


def submit_answer(session_id, location_key, answer):
    resp = requests.post(
        f"{BACKEND}/api/games/{session_id}/answer",
        json={"location_key": location_key, "answer": answer},
    )
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

    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("🔄 Play Again", use_container_width=True):
            st.session_state.session_id = new_game()
            st.session_state.selected_location = None
            st.session_state.current_question = None
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
    st.metric("Score", f"{game_state['score']}/{len(game_state['answered_locations'])}")

with col_progress:
    st.metric("Progress", f"{len(game_state['answered_locations'])}/{game_state['total']}")

with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

# ---------------------------------------------------------------------------
# Map + trivia panel
# ---------------------------------------------------------------------------
locations = get_locations()
location_keys = [loc["key"] for loc in locations]

col_map, col_trivia = st.columns([2, 1])

with col_map:
    st.subheader("Map")
    selected_param = st.session_state.selected_location or ""
    map_url = f"{BACKEND}/api/map?selected={requests.utils.quote(selected_param)}"
    map_html = requests.get(map_url).text
    components.html(map_html, height=500)

with col_trivia:
    st.subheader("Trivia")

    dropdown_options = [""] + location_keys
    current_index = (
        dropdown_options.index(st.session_state.selected_location)
        if st.session_state.selected_location in dropdown_options
        else 0
    )

    selected = st.selectbox(
        "Select a location for trivia:",
        dropdown_options,
        index=current_index,
        key="location_dropdown",
    )

    if selected != st.session_state.selected_location:
        st.session_state.selected_location = selected or None
        st.session_state.current_question = None
        st.rerun()

    if not st.session_state.selected_location:
        st.info("👆 Select a location from the dropdown to start the trivia!")
    else:
        location_key = st.session_state.selected_location
        already_answered = location_key in game_state["answered_locations"]

        # Show building image
        loc_data = next((l for l in locations if l["key"] == location_key), None)
        if loc_data:
            img_path = loc_data["img_path"]
            if os.path.exists(img_path):
                st.image(img_path, width=300)

        if already_answered:
            st.info("✅ You've already answered this one. Select another building!")
            if st.button("Try Another Location"):
                st.session_state.selected_location = None
                st.session_state.current_question = None
                st.rerun()
        else:
            # Fetch and cache question (avoid reshuffling on every rerun)
            if (
                st.session_state.current_question is None
                or st.session_state.current_question["key"] != location_key
            ):
                st.session_state.current_question = get_question(location_key)

            q = st.session_state.current_question
            st.write(f"**{q['question']}**")
            st.write("Choose your answer:")

            col_a, col_b = st.columns(2)
            options = q["options"]

            def make_answer_handler(opt):
                result = submit_answer(session_id, location_key, opt)
                if result["correct"]:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Answer: {result['correct_answer']}")
                st.session_state.current_question = None
                st.rerun()

            with col_a:
                if len(options) > 0 and st.button(f"A) {options[0]}", key=f"opt0_{location_key}"):
                    make_answer_handler(options[0])
                if len(options) > 2 and st.button(f"C) {options[2]}", key=f"opt2_{location_key}"):
                    make_answer_handler(options[2])

            with col_b:
                if len(options) > 1 and st.button(f"B) {options[1]}", key=f"opt1_{location_key}"):
                    make_answer_handler(options[1])
                if len(options) > 3 and st.button(f"D) {options[3]}", key=f"opt3_{location_key}"):
                    make_answer_handler(options[3])
