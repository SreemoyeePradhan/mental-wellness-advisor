import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from datetime import datetime
from backend import (
    detect_emotion,
    update_mood_history,
    get_mood_history,
    get_session_summary,
    get_user_profile,
    get_daily_tip,
    get_guided_exercises,
    get_resources
)
from gtts import gTTS

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

DISTRESS_KEYWORDS = ["suicidal", "hopeless", "can't go on", "end my life", "worthless"]

def build_context(messages, last_n=5):
    context = ""
    for msg in messages[-last_n:]:
        role = "User" if msg["role"] == "user" else "AI"
        context += f"{role}: {msg['content']}\n"
    return context

def is_question(text):
    question_words = ["what", "why", "how", "when", "where", "do", "does", "is", "are", "?"]
    return any(word in text.lower() for word in question_words) or text.strip().endswith("?")

def translate_text(text, target_lang="en"):
    try:
        if not target_lang or target_lang == "en":
            return text
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text

def strip_markdown_for_tts(text: str) -> str:
    if not text:
        return text
    t = text
    t = re.sub(r"```.*?```", "", t, flags=re.DOTALL)
    t = re.sub(r"`(.+?)`", r"\1", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"__(.+?)__", r"\1", t)
    t = re.sub(r"_(.+?)_", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\n{2,}", "\n", t)
    t = t.replace("*", "").replace("`", "")
    return t.strip()

def adjust_tone(emotion, user_profile):
    tone = user_profile.get("preferences", {}).get("tone", "neutral")
    if tone != "neutral":
        return f"Your tone should be {tone}."
    if emotion == "joy":
        return "Your tone should be upbeat and encouraging."
    elif emotion == "sadness":
        return "Your tone should be gentle, supportive, and empathetic."
    elif emotion == "anger":
        return "Your tone should be calm, understanding, and soothing."
    else:
        return "Your tone should be neutral and balanced."

def get_wellness_response(user_input, conversation_messages, previous_suggestions=None, target_lang="en", habits_summary="", user_id=None, profile=None):
    if previous_suggestions is None:
        previous_suggestions = []

    context = build_context(conversation_messages)
    emotion = detect_emotion(user_input)
    update_mood_history(user_id, emotion, emotion)

    user_profile = profile or get_user_profile(user_id)
    tone_instruction = adjust_tone(emotion, user_profile)
    session_summary = get_session_summary(user_id)
    mood_history = get_mood_history(user_id)
    mood_summary = f"Your recent mood history: {mood_history[-5:]}" if mood_history else ""

    if is_question(user_input):
        user_intro = f"User asked a question: {user_input}"
    else:
        user_intro = f"User stated: {user_input}"

    previous_suggestions_text = ""
    if previous_suggestions:
        previous_suggestions_text = f"Previous AI suggestions: {previous_suggestions}\n"

    distress_alert = ""
    if any(word in user_input.lower() for word in DISTRESS_KEYWORDS):
        distress_alert = (
            "⚠️ It sounds like you're in severe distress. "
            "Please consider calling a local helpline:\n"
            "🇮🇳 India: 9152987821 (Vandrevala Foundation)\n"
            "🇺🇸 USA: 988 (Suicide & Crisis Lifeline)\n"
            "🇬🇧 UK: 116 123 (Samaritans)\n"
            "Reach out to a friend, family member, or professional."
        )

    daily_tip = get_daily_tip()
    guided_exercises = get_guided_exercises(emotion, profile=user_profile)
    resources = get_resources(emotion, profile=user_profile)

    prompt = (
        "You are a kind and supportive mental wellness AI assistant.\n"
        f"{tone_instruction}\n"
        f"Session summary: {session_summary}\n"
        f"Mood history: {mood_summary}\n"
        f"Conversation context:\n{context}\n"
        f"{user_intro}\n"
        f"{previous_suggestions_text}"
        f"{distress_alert}\n"
        f"User habits summary: {habits_summary}\n"
        f"Daily wellness tip: {daily_tip}\n"
        f"Guided exercises: {guided_exercises}\n"
        f"Resources: {resources}\n"
        "Respond empathetically, provide guidance, suggest follow-up exercises, "
        "and keep responses concise and supportive."
    )

    try:
        response = model.generate_content(prompt)
        display_text = response.text.strip()
        translated_display = translate_text(display_text, target_lang)
        tts_ready = strip_markdown_for_tts(translated_display)
        return {
            "text": translated_display,
            "tts_text": tts_ready,
            "emotion": emotion,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        err_text = f"⚠️ Error contacting Gemini API: {str(e)}"
        return {
            "text": err_text,
            "tts_text": strip_markdown_for_tts(err_text),
            "emotion": emotion,
            "timestamp": datetime.utcnow().isoformat()
        }

def synthesize_speech_and_save(text, user_id="default_user", lang="en"):
    from backend import make_audio_filename
    try:
        audio_path = make_audio_filename(user_id, role="ai")
        tts = gTTS(text=text, lang=lang)
        tts.save(audio_path)
        return audio_path
    except Exception:
        try:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts = gTTS(text=text, lang=lang)
            tts.save(tmp.name)
            return tmp.name
        except Exception:
            return None
