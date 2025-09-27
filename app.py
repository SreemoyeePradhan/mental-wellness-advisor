# app.py (full updated file with full sidebar translations)
import os
import streamlit as st
import time
from datetime import datetime, timezone
import streamlit.components.v1 as components
from main import get_wellness_response, synthesize_speech_and_save
from backend import (
    detect_mood,
    detect_emotion,
    get_emoji_for_mood,
    log_conversation,
    log_summary,
    get_conversation,
    update_habits,
    update_mood_history,
    get_mood_history,
    get_session_summary,
    get_user_profile,
    update_user_profile,
    add_goal,
    update_goal_progress,
    get_goals,
    get_daily_tip,
    get_guided_exercises,
    get_resources,
    get_all_profiles,
    create_profile,
    translate_text
)

AUDIO_DIR = os.path.join(os.getcwd(), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

st.set_page_config(page_title="🧘 Mental Wellness AI", page_icon="🧘", layout="centered")

# --------------------------
# Configuration / Defaults
# --------------------------
language_options = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de"
}

if "mode" not in st.session_state:
    st.session_state.mode = "dark"
mode_options = ["light", "dark"]
if st.session_state.mode not in mode_options:
    st.session_state.mode = "dark"

if "all_profiles" not in st.session_state:
    st.session_state.all_profiles = get_all_profiles() or ["default_user"]

# --------------------------
# Profile selection / creation
# --------------------------
with st.sidebar.expander(translate_text("👤 Select / Create Profile", "en")):
    profile_choice_list = st.session_state.all_profiles + [translate_text("Create New Profile", "en")]
    profile_selection = st.selectbox(
        translate_text("Choose Profile", "en"),
        profile_choice_list
    )

    if profile_selection == translate_text("Create New Profile", "en"):
        new_profile_name = st.text_input(translate_text("Enter New Profile Name", "en"))
        if st.button(translate_text("Create Profile", "en")):
            if new_profile_name and new_profile_name not in st.session_state.all_profiles:
                create_profile(new_profile_name)
                st.session_state.all_profiles.append(new_profile_name)
                st.session_state.user_id = new_profile_name
                st.success(translate_text(f"Profile '{new_profile_name}' created!", "en"))
            else:
                st.warning(translate_text("Enter a unique profile name.", "en"))
    else:
        st.session_state.user_id = profile_selection

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

user_id = st.session_state.user_id
profile = get_user_profile(user_id)

if "loaded_history" not in st.session_state or st.session_state.user_id != user_id:
    stored = get_conversation(user_id)
    profile = get_user_profile(user_id)
    st.session_state.habits_summary = profile.get("habits_summary", "User is new to wellness tracking.")
    st.session_state.messages = stored.get("conversation", [])
    st.session_state.previous_suggestions = [m["content"] for m in st.session_state.messages if m.get("role") == "ai"]
    st.session_state.loaded_history = True

profile = get_user_profile(user_id)

# --------------------------
# Selected language handling
# --------------------------
profile_lang_name = profile.get("preferences", {}).get("language", "English")
if profile_lang_name not in language_options:
    reversed_map = {v: k for k, v in language_options.items()}
    profile_lang_name = reversed_map.get(profile_lang_name, "English")

if "selected_lang_name" not in st.session_state:
    st.session_state.selected_lang_name = profile_lang_name
if "selected_lang_code" not in st.session_state:
    st.session_state.selected_lang_code = language_options.get(st.session_state.selected_lang_name, "en")

lang_choice = st.sidebar.selectbox(
    translate_text("Select Language", profile_lang_name),
    list(language_options.keys()),
    index=list(language_options.keys()).index(st.session_state.selected_lang_name)
)

if lang_choice != st.session_state.selected_lang_name:
    st.session_state.selected_lang_name = lang_choice
    st.session_state.selected_lang_code = language_options.get(lang_choice, "en")
    profile["preferences"] = profile.get("preferences", {})
    profile["preferences"]["language"] = lang_choice
    update_user_profile(user_id, profile)

UI_LANG_NAME = st.session_state.selected_lang_name
BACKEND_LANG_CODE = st.session_state.selected_lang_code

# --------------------------
# Theme styling
# --------------------------
if st.session_state.mode == "dark":
    st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: #ddd; }
        .chat-bubble { background: #2a2a2a; color: #ddd; border-radius:12px; padding:12px; margin:8px 0;}
        .user-bubble { background: #064663; color: white; border-radius:12px; padding:12px; margin:8px 0; text-align:right;}
        .meta { font-size:11px; color:#bbb; }
        .summary-button { color:white; background:#0078d4; padding:8px; border-radius:8px; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp { background-color: #ffffff; color: #0b2533; }
        .chat-bubble { background: #f1f9fc; color: #0b2533; border-radius:12px; padding:12px; margin:8px 0;}
        .user-bubble { background: #e6f7ff; color: #0b2533; border-radius:12px; padding:12px; margin:8px 0; text-align:right;}
        .meta { font-size:11px; color:#556b74; }
        .summary-button { color:black; background:#e0e0e0; padding:8px; border-radius:8px; }
        </style>
    """, unsafe_allow_html=True)

# --------------------------
# Header
# --------------------------
st.title("🧘 " + translate_text("Mental Wellness AI Advisor", UI_LANG_NAME))
st.markdown(translate_text("I’m here to listen and support your mental wellness journey. (Not a substitute for professional help.)", UI_LANG_NAME))

# --------------------------
# Profile settings
# --------------------------
with st.sidebar.expander(translate_text("🧑 Profile Settings", UI_LANG_NAME)):
    profile["name"] = st.text_input(translate_text("Name", UI_LANG_NAME), profile.get("name", ""))
    profile["age"] = st.number_input(translate_text("Age", UI_LANG_NAME), min_value=0, max_value=120, value=profile.get("age", 0))
    profile["preferences"] = profile.get("preferences", {"language": profile_lang_name, "tone": "neutral"})
    profile["preferences"]["language"] = st.session_state.selected_lang_name
    profile["preferences"]["tone"] = st.selectbox(
        translate_text("Tone Preference", UI_LANG_NAME),
        ["neutral", "supportive", "encouraging", "calm"],
        index=["neutral", "supportive", "encouraging", "calm"].index(profile.get("preferences", {}).get("tone", "neutral"))
    )
    if st.button(translate_text("Save Profile", UI_LANG_NAME)):
        update_user_profile(user_id, profile)
        st.success(translate_text("Profile updated!", UI_LANG_NAME))


# --------------------------
# Chat rendering helpers
# --------------------------
def render_message(msg):
    role = msg.get("role", "ai")
    content = msg.get("content", "")
    ts = msg.get("timestamp", "")
    mood = msg.get("mood") or detect_mood(content if role == "user" else "")
    emotion = msg.get("emotion") or detect_emotion(content)
    emoji = msg.get("emoji") or get_emoji_for_mood(emotion or mood)
    audio_path = msg.get("audio_path")

    if role == "user":
        html = f"""
        <div class="user-bubble">
            <div class="meta">{ts} • You</div>
            <div style="font-size:18px; margin-top:6px;">{content}</div>
        </div>
        """
    else:
        html = f"""
        <div class="chat-bubble">
            <div class="meta">AI {emoji} • {ts}</div>
            <div style="font-size:18px; margin-top:6px;">{content}</div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)
    if role == "ai" and audio_path and os.path.exists(audio_path):
        st.audio(audio_path)

# Render existing messages
if "messages" not in st.session_state:
    st.session_state.messages = st.session_state.get("messages", [])
for msg in st.session_state.messages:
    render_message(msg)

# --------------------------
# Chat input and response
# --------------------------
prompt = st.chat_input(translate_text("How are you feeling today?", UI_LANG_NAME))

if prompt:
    now_iso = datetime.now(timezone.utc).isoformat()
    user_msg = {
        "role": "user",
        "content": prompt,
        "timestamp": now_iso,
        "mood": detect_mood(prompt),
        "emotion": detect_emotion(prompt),
        "emoji": get_emoji_for_mood(detect_emotion(prompt)),
        "audio_path": None
    }
    st.session_state.messages.append(user_msg)
    render_message(user_msg)

    ai_result = get_wellness_response(
        prompt,
        conversation_messages=st.session_state.messages,
        previous_suggestions=st.session_state.previous_suggestions,
        target_lang=BACKEND_LANG_CODE,               # model / tts expects ISO code
        habits_summary=st.session_state.habits_summary,
        user_id=user_id,
        profile=profile
    )
    ai_text = ai_result.get("text", "")
    ai_emotion = ai_result.get("emotion", detect_emotion(ai_text))

    placeholder = st.empty()
    displayed = ""
    for ch in ai_text:
        displayed += ch
        placeholder.markdown(
            f"<div class='chat-bubble'><div class='meta'>AI {get_emoji_for_mood(ai_emotion)} • {datetime.now(timezone.utc).isoformat()}</div><div style='font-size:18px; margin-top:6px;'>{displayed}</div></div>",
            unsafe_allow_html=True
        )
        time.sleep(0.01)
    placeholder.empty()

    ai_msg = {
        "role": "ai",
        "content": ai_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "emotion": ai_emotion,
        "emoji": get_emoji_for_mood(ai_emotion),
        "audio_path": None
    }
    audio_file = synthesize_speech_and_save(ai_text, user_id=user_id, lang=BACKEND_LANG_CODE)
    if audio_file:
        ai_msg["audio_path"] = audio_file

    st.session_state.messages.append(ai_msg)
    render_message(ai_msg)
    st.session_state.previous_suggestions.append(ai_text)

    try:
        log_conversation(user_id, [user_msg, ai_msg])
        update_mood_history(user_id, user_msg["mood"], user_msg["emotion"])
    except Exception as e:
        st.warning(translate_text("Could not log conversation: ", UI_LANG_NAME) + str(e))

# --------------------------
# Session summary button
# --------------------------
st.markdown("<div class='summary-button'>", unsafe_allow_html=True)
if st.button(translate_text("📄 Summarize this session", UI_LANG_NAME)):
    summary_result = get_wellness_response(
        "Please provide a concise session summary and mood trend.",
        st.session_state.messages,
        previous_suggestions=st.session_state.previous_suggestions,
        target_lang=BACKEND_LANG_CODE,
        habits_summary=st.session_state.habits_summary,
        user_id=user_id,
        profile=profile
    )
    summary_text = summary_result.get("text", "")
    st.markdown("**" + translate_text("📊 Session Summary:", UI_LANG_NAME) + "**")
    st.markdown(summary_text)
    log_summary(user_id, summary_text)
st.markdown("</div>", unsafe_allow_html=True)

# --------------------------
# Habits tracking
# --------------------------
st.sidebar.markdown("### " + translate_text("Your habits / tracking", UI_LANG_NAME))
habit_text = st.sidebar.text_area(translate_text("Describe your recent wellness habits", UI_LANG_NAME), value=st.session_state.habits_summary or "")
if st.sidebar.button(translate_text("Save habits", UI_LANG_NAME)):
    update_habits(user_id, habit_text)
    st.session_state.habits_summary = habit_text
    st.sidebar.success(translate_text("Habits saved.", UI_LANG_NAME))

# --------------------------
# Goals tracking
# --------------------------
with st.sidebar.expander(translate_text("🎯 Wellness Goals", UI_LANG_NAME)):
    goals = get_goals(user_id)
    for goal in goals:
        status_display = goal.get("progress", "Not Started")
        if status_display == "Completed":
            st.markdown(f"<span style='color:green; font-weight:bold;'>✔ {goal['text']} ({translate_text('Completed', UI_LANG_NAME)})</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"- {goal['text']}")

        progress_options = [
            translate_text("Not Started", UI_LANG_NAME),
            translate_text("Started", UI_LANG_NAME),
            translate_text("In Progress", UI_LANG_NAME),
            translate_text("Completed", UI_LANG_NAME)
        ]

        # Map stored progress (English) to translated index if necessary
        stored_progress_en = goal.get("progress", "Not Started")
        # Use English progress value to find index in progress_options by comparing translated strings
        # Build an English->translated lookup
        en_to_trans = {
            "Not Started": translate_text("Not Started", UI_LANG_NAME),
            "Started": translate_text("Started", UI_LANG_NAME),
            "In Progress": translate_text("In Progress", UI_LANG_NAME),
            "Completed": translate_text("Completed", UI_LANG_NAME),
        }
        translated_current = en_to_trans.get(stored_progress_en, en_to_trans["Not Started"])
        try:
            idx = progress_options.index(translated_current)
        except ValueError:
            idx = 0

        status = st.selectbox(
            translate_text("Current Status for above-mentioned goal", UI_LANG_NAME),
            progress_options,
            index=idx,
            key=f"goal_{goal['goal_id']}_status"
        )

        if st.button(translate_text("Update Current Status of above-mentioned Goal", UI_LANG_NAME), key=f"update_{goal['goal_id']}"):
            # Map translated status back to English to store (reverse mapping)
            trans_to_en = {v: k for k, v in en_to_trans.items()}
            status_en = trans_to_en.get(status, "Not Started")
            update_goal_progress(user_id, goal["goal_id"], status_en)
            st.sidebar.success(translate_text("Goal updated!", UI_LANG_NAME))

    new_goal = st.text_input(translate_text("Add new wellness goal", UI_LANG_NAME))
    if st.button(translate_text("Add Goal", UI_LANG_NAME)):
        add_goal(user_id, new_goal)
        st.sidebar.success(translate_text("Goal added!", UI_LANG_NAME))

# --------------------------
# Daily Tip & Resources (translated via backend)
# --------------------------
st.sidebar.markdown("### " + translate_text("🌿 Daily Wellness Tip", UI_LANG_NAME))
st.sidebar.info(get_daily_tip(profile=profile))  # backend translates based on profile's language/tone

st.sidebar.markdown("### " + translate_text("📚 Guided Exercises & Resources", UI_LANG_NAME))
emotion = detect_emotion(prompt or "")
exercises = get_guided_exercises(emotion, profile=profile)
resources = get_resources(emotion, profile=profile)

for ex in exercises:
    st.sidebar.markdown(f"- {ex}")

for res in resources:
    # resource titles are already translated by backend if profile language set
    st.sidebar.markdown(f"- [{res.get('title', res)}]({res.get('url', '#')})")
