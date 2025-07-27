import streamlit as st
import folium
import streamlit.components.v1 as components
import base64
import os
import time
from location_list import locations

# Initialize session state for selected location and score
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None
if 'user_scores' not in st.session_state:
    st.session_state.user_scores = {}
if 'answered_questions' not in st.session_state:
    st.session_state.answered_questions = set()
if 'game_start_time' not in st.session_state:
    st.session_state.game_start_time = None
if 'game_over' not in st.session_state:
    st.session_state.game_over = False
if 'timer_started' not in st.session_state:
    st.session_state.timer_started = False
if 'splash_start_time' not in st.session_state:
    st.session_state.splash_start_time = time.time()
if 'show_splash' not in st.session_state:
    st.session_state.show_splash = True


def start_game_timer():
    """Start the game timer"""
    if not st.session_state.timer_started:
        st.session_state.game_start_time = time.time()
        st.session_state.timer_started = True


def get_remaining_time():
    """Get remaining time in seconds"""
    if not st.session_state.game_start_time:
        return 90  # 1.30 minutes
    
    elapsed = time.time() - st.session_state.game_start_time
    remaining = max(0, 90 - elapsed)
    return remaining


def check_game_over():
    """Check if game should end"""
    remaining_time = get_remaining_time()
    total_questions = len(locations)
    answered_count = len(st.session_state.answered_questions)
    
    # Game over if time runs out or all questions answered
    if remaining_time <= 0 or answered_count >= total_questions:
        st.session_state.game_over = True
        return True
    return False


def handle_answer(location_key, selected_answer, correct_answer):
    """Handle user's answer selection"""
    if st.session_state.game_over:
        return
        
    if location_key not in st.session_state.answered_questions:
        # Start timer on first answer
        start_game_timer()
        
        if selected_answer == correct_answer:
            st.session_state.user_scores[location_key] = True
            st.success("Correct! 🎉")
        else:
            st.session_state.user_scores[location_key] = False
            st.error(f"Incorrect! The correct answer is: {correct_answer}")
        st.session_state.answered_questions.add(location_key)
        
        # Check if game should end
        check_game_over()

# Map center
center = [51.52467300356322, -0.13438961571612038]

# Create a Folium map widget with dynamic zoom based on selected location
if st.session_state.selected_location:
    # Find the selected location for zooming
    selected_loc_data = None
    for loc in locations:
        if loc['key'] == st.session_state.selected_location:
            selected_loc_data = loc
            break
    
    if selected_loc_data:
        # Create map centered on selected location with higher zoom
        m = folium.Map(
            location=[selected_loc_data["location"]["lat"], selected_loc_data["location"]["lng"]], 
            zoom_start=16
        )
    else:
        m = folium.Map(location=center, zoom_start=13)
else:
    m = folium.Map(location=center, zoom_start=13)

# Add markers with customized HTML popups
for loc in locations:
    # Convert image to base64 for embedding
    img_path = loc['img_path']
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()
            img_src = f"data:image/jpeg;base64,{img_base64}"
    else:
        img_src = ""
    
    # Check if this is the selected location
    is_selected = st.session_state.selected_location == loc['key']
    
    popup_html = f"""
    <div style="width: 280px; font-family: Arial, sans-serif;">
      <h4 style="color: #003366; margin-bottom: 10px;">
        {loc['key']} {' ⭐ SELECTED' if is_selected else ''}
      </h4>
      {f'<img src="{img_src}" width="260" alt="Image of {loc["key"]}" style="border-radius: 5px; margin-bottom: 10px;" />' if img_src else ''}
      <p style="font-weight: bold; color: #333; margin-bottom: 8px;">
        {'This location is currently selected for trivia!' if is_selected else 'Use the dropdown to select this location for trivia!'}
      </p>
    </div>
    """
    
    # Use different marker colors for selected vs unselected
    marker_color = 'red' if is_selected else 'blue'
    marker_icon = folium.Icon(color=marker_color, icon='star' if is_selected else 'info-sign')
    
    folium.Marker(
        location=[loc["location"]["lat"], loc["location"]["lng"]],
        popup=folium.Popup(popup_html, max_width=320),
        icon=marker_icon
    ).add_to(m)

# Streamlit app UI
# Check if we should show splash screen
if st.session_state.show_splash:
    # Check if 2 seconds have passed
    elapsed_time = time.time() - st.session_state.splash_start_time
    
    if elapsed_time < 2.0:
        # Hide Streamlit UI elements for fullscreen effect
        st.markdown(
            """
            <style>
                .main .block-container {
                    padding-top: 0rem;
                    padding-bottom: 0rem;
                    padding-left: 0rem;
                    padding-right: 0rem;
                }
                header[data-testid="stHeader"] {
                    display: none;
                }
                .stApp > header {
                    display: none;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Show fullscreen splash screen
        st.markdown(
            """
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            ">
                <div style="text-align: center; color: white;">
                    <h1 style="font-size: 5em; margin: 0; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                        UCL Guessr
                    </h1>
                    <p style="font-size: 2em; margin-top: 30px; opacity: 0.9;">
                        Interactive Campus Trivia Game
                    </p>
                    <div style="margin-top: 50px;">
                        <div style="
                            width: 80px; 
                            height: 80px; 
                            border: 6px solid rgba(255,255,255,0.3);
                            border-top: 6px solid white;
                            border-radius: 50%;
                            animation: spin 1s linear infinite;
                            margin: 0 auto;
                        "></div>
                    </div>
                    <p style="font-size: 1.2em; margin-top: 30px; opacity: 0.7;">
                        Loading...
                    </p>
                </div>
            </div>
            
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Auto-refresh to check time
        time.sleep(0.1)
        st.rerun()
    else:
        # Hide splash screen and show main game
        st.session_state.show_splash = False
        st.rerun()
    
    # Stop execution here to only show splash
    st.stop()

# Load and encode the UCL logo
logo_path = "src/images/logo.png"
logo_src = ""
if os.path.exists(logo_path):
    with open(logo_path, "rb") as img_file:
        logo_base64 = base64.b64encode(img_file.read()).decode()
        logo_src = f"data:image/png;base64,{logo_base64}"

# Create title with logo
if logo_src:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <img src="{logo_src}" alt="UCL Logo" style="height: 4rem; margin-right: 20px;">
            <h1 style="margin: 0; font-size: 4rem; color: #262730;">UCL Guessr</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <h1 style="margin: 0; font-size: 4rem; color: #262730;">UCL Guessr</h1>
        """,
        unsafe_allow_html=True
    )

# Check if game is over and show modal
check_game_over()

if st.session_state.game_over:
    # Show game over modal
    correct_answers = sum(st.session_state.user_scores.values())
    total_questions = len(locations)
    
    # Create a prominent game over display
    st.error("⏰ GAME OVER!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                color: white;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            ">
                <h2 style="margin: 0; font-size: 2.5em;">🎯 Final Score</h2>
                <h1 style="margin: 20px 0; font-size: 4em; font-weight: bold;">{correct_answers}/{total_questions}</h1>
                <p style="font-size: 1.2em; margin: 10px 0;">
                    You answered {correct_answers} out of {total_questions} questions correctly!
                </p>
                <p style="font-size: 1em; opacity: 0.9;">
                    {f"🏆 Excellent!" if correct_answers >= 8 else f"👍 Good job!" if correct_answers >= 6 else f"📚 Keep studying!"}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Reset game button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Play Again", use_container_width=True):
            # Reset all game state
            st.session_state.selected_location = None
            st.session_state.user_scores = {}
            st.session_state.answered_questions = set()
            st.session_state.game_start_time = None
            st.session_state.game_over = False
            st.session_state.timer_started = False
            st.session_state.show_splash = True
            st.session_state.splash_start_time = time.time()
            st.rerun()
    
    st.stop()

# Display timer and game status
st.markdown("---")
col_timer, col_score, col_progress, col_refresh = st.columns([2, 1, 1, 1])

with col_timer:
    remaining_time = get_remaining_time()
    if st.session_state.timer_started:
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        
        if remaining_time <= 0:
            st.error("⏰ TIME'S UP!")
        elif remaining_time <= 30:
            st.markdown(f"🔴 **Time:** {minutes:02d}:{seconds:02d}")
        elif remaining_time <= 60:
            st.markdown(f"🟠 **Time:** {minutes:02d}:{seconds:02d}")
        else:
            st.markdown(f"🟢 **Time:** {minutes:02d}:{seconds:02d}")
    else:
        st.info("⏱️ Timer: Ready")

with col_score:
    if st.session_state.user_scores:
        correct_count = sum(st.session_state.user_scores.values())
        total_answered = len(st.session_state.answered_questions)
        st.metric("Score", f"{correct_count}/{total_answered}")
    else:
        st.metric("Score", "0/0")

with col_progress:
    total_questions = len(locations)
    answered_count = len(st.session_state.answered_questions)
    st.metric("Progress", f"{answered_count}/{total_questions}")

with col_refresh:
    if st.button("🔄 Refresh", help="Update timer"):
        st.rerun()

# Check for game over due to time (only when user interacts)
if st.session_state.timer_started:
    remaining_time = get_remaining_time()
    if remaining_time <= 0 and not st.session_state.game_over:
        st.session_state.game_over = True
        st.rerun()

# Check for map selection via URL parameters first
query_params = st.query_params
if 'selected_location' in query_params:
    new_selection = query_params['selected_location']
    if new_selection != st.session_state.selected_location:
        st.session_state.selected_location = new_selection
        # Clear the URL parameter after processing
        st.query_params.clear()
        st.rerun()

# Create two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Map")
    if st.session_state.selected_location:
        st.write(f"📍 **Selected:** {st.session_state.selected_location}")
    else:
        st.write("📍 **Selected:** None")

    # Display the map with enhanced interactivity
    map_html = m._repr_html_()
    components.html(map_html, width=700, height=500)

with col2:
    st.subheader("Trivia")
    
    # Location selection dropdown
    location_names = [loc['key'] for loc in locations]
    
    # Set the dropdown index based on session state
    if st.session_state.selected_location and st.session_state.selected_location in location_names:
        default_index = location_names.index(st.session_state.selected_location) + 1
    else:
        default_index = 0
    
    selected_location = st.selectbox(
        "Select a location for trivia:",
        [""] + location_names,
        index=default_index,
        key="location_dropdown"
    )
    
    # Handle dropdown selection change
    if selected_location and selected_location != st.session_state.selected_location:
        st.session_state.selected_location = selected_location
        st.rerun()
    elif not selected_location and st.session_state.selected_location:
        # Handle case where user selects empty option
        st.session_state.selected_location = None
        st.rerun()
    
    # Show trivia for selected location
    if st.session_state.selected_location:
        # Find the selected location data
        current_loc = None
        for loc in locations:
            if loc['key'] == st.session_state.selected_location:
                current_loc = loc
                break
        
        if current_loc:
            st.write(f"**Location:** {current_loc['key']}")
            
            # Show image
            img_path = current_loc['img_path']
            if os.path.exists(img_path):
                st.image(img_path, width=300)
            
            # Show trivia question
            st.write("**Trivia Question:**")
            st.write(current_loc['trivia_question'])
            
            # Create answer options
            options = [
                current_loc['trivia_opt1'],
                current_loc['trivia_opt2'], 
                current_loc['trivia_opt3'],
                current_loc['trivia_answer']
            ]
            
            # Check if already answered or game over
            location_key = current_loc['key']
            if st.session_state.game_over:
                st.info("⏰ Game Over! Click 'Play Again' to restart.")
            elif location_key in st.session_state.answered_questions:
                # Show previous result
                if st.session_state.user_scores.get(location_key, False):
                    st.success(f"✅ Correct! Answer: {current_loc['trivia_answer']}")
                else:
                    st.error(f"❌ Incorrect. Correct answer: {current_loc['trivia_answer']}")
                
                if st.button("Try Another Location", key=f"reset_{location_key}"):
                    st.session_state.selected_location = None
                    st.rerun()
            else:
                # Show interactive buttons
                st.write("Choose your answer:")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"A) {current_loc['trivia_opt1']}", key=f"a_{location_key}"):
                        handle_answer(location_key, current_loc['trivia_opt1'], current_loc['trivia_answer'])
                        st.rerun()
                    
                    if st.button(f"C) {current_loc['trivia_opt3']}", key=f"c_{location_key}"):
                        handle_answer(location_key, current_loc['trivia_opt3'], current_loc['trivia_answer'])
                        st.rerun()
                
                with col_b:
                    if st.button(f"B) {current_loc['trivia_opt2']}", key=f"b_{location_key}"):
                        handle_answer(location_key, current_loc['trivia_opt2'], current_loc['trivia_answer'])
                        st.rerun()
                    
                    if st.button(f"D) {current_loc['trivia_answer']}", key=f"d_{location_key}"):
                        handle_answer(location_key, current_loc['trivia_answer'], current_loc['trivia_answer'])
                        st.rerun()
    else:
        st.info("👆 Select a location from the map or dropdown to start the trivaia!")
