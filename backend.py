import os
import json
import certifi
import uuid
import random
from dotenv import load_dotenv
from pymongo import MongoClient, errors
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from deep_translator import GoogleTranslator

load_dotenv()

AUDIO_CACHE_DIR = os.path.join(os.getcwd(), "audio_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

MONGO_URI = os.getenv("MONGO_URI")
try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000
    )
    client.server_info()
    db = client["sreemoyee"]
    collection = db["pradhan"]
    MONGO_AVAILABLE = True
except errors.ServerSelectionTimeoutError:
    print("⚠️ MongoDB not reachable, using local JSON storage.")
    MONGO_AVAILABLE = False
    LOCAL_DB_FILE = "local_chat_storage.json"

analyzer = SentimentIntensityAnalyzer()

MOOD_EMOJI_MAP = {
    "happy": "🙂",
    "calm": "😌",
    "stressed": "😟",
    "sad": "😢",
    "joy": "😁",
    "content": "😊",
    "neutral": "😐",
    "anxiety": "😰",
    "anger": "😠"
}

LANGUAGE_CODE_MAP = {
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "hindi": "hi",
    "albanian": "sq",
    "afrikaans": "af",
    "amharic": "am",
    "arabic": "ar",
    "bengali": "bn",
    "chinese": "zh",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
    "turkish": "tr",
    "urdu": "ur"
}

def translate_text(text, target_lang="en"):
    """Translate a single text string to target language."""
    try:
        target_lang_code = LANGUAGE_CODE_MAP.get(target_lang.lower(), "en")
        if target_lang_code == "en":
            return text
        return GoogleTranslator(source='auto', target=target_lang_code).translate(text)
    except Exception as e:
        print(f"Translation error ({target_lang}): {e}")
        return text

def translate_ui_labels(labels_dict, target_lang="en"):
    """
    Translate all sidebar/UI labels (headings, dropdowns, options) into target language.
    labels_dict: dict { "key": "English text" }
    Returns translated dict.
    """
    translated = {}
    for key, text in labels_dict.items():
        translated[key] = translate_text(text, target_lang)
    return translated

def detect_mood(user_message):
    sentiment = analyzer.polarity_scores(user_message)
    if sentiment["compound"] >= 0.5:
        return "happy"
    elif sentiment["compound"] <= -0.5:
        return "sad"
    elif sentiment["compound"] > 0:
        return "calm"
    else:
        return "stressed"

def detect_emotion(user_message):
    sentiment = analyzer.polarity_scores(user_message)
    compound = sentiment["compound"]
    if compound >= 0.6:
        return "joy"
    elif 0.2 <= compound < 0.6:
        return "content"
    elif -0.2 < compound < 0.2:
        return "neutral"
    elif -0.6 < compound <= -0.2:
        return "anxiety"
    else:
        return "anger"

def get_emoji_for_mood(mood_or_emotion):
    return MOOD_EMOJI_MAP.get(mood_or_emotion, "🧠")

def load_local_data():
    if os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_local_data(data):
    with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_conversation(user_id):
    if MONGO_AVAILABLE:
        doc = collection.find_one({"user_id": user_id})
        if not doc:
            return {"user_id": user_id, "conversation": [], "last_updated": None, "habits_summary": None, "mood_history": [], "goals": [], "profile": {}}
        doc.setdefault("conversation", [])
        doc.setdefault("session_summaries", [])
        doc.setdefault("habits_summary", "User is new to wellness tracking.")
        doc.setdefault("mood_history", [])
        doc.setdefault("goals", [])
        doc.setdefault("profile", {})
        return doc
    else:
        data = load_local_data()
        return data.get(user_id, {"user_id": user_id, "conversation": [], "last_updated": None, "habits_summary": "User is new to wellness tracking.", "mood_history": [], "goals": [], "profile": {}})

def log_conversation(user_id, messages):
    for msg in messages:
        msg.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        msg.setdefault("mood", None)
        msg.setdefault("emotion", None)
        msg.setdefault("emoji", None)
        msg.setdefault("audio_path", None)

    if MONGO_AVAILABLE:
        collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_updated": datetime.now(timezone.utc)}, "$push": {"conversation": {"$each": messages}}},
            upsert=True
        )
    else:
        data = load_local_data()
        if user_id not in data:
            data[user_id] = {"conversation": []}
        data[user_id]["conversation"].extend(messages)
        data[user_id]["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_local_data(data)

def log_summary(user_id, summary_text):
    if MONGO_AVAILABLE:
        collection.update_one(
            {"user_id": user_id},
            {"$push": {"session_summaries": {"summary": summary_text, "timestamp": datetime.now(timezone.utc)}}},
            upsert=True
        )
    else:
        data = load_local_data()
        if user_id not in data:
            data[user_id] = {"session_summaries": []}
        data[user_id].setdefault("session_summaries", []).append({
            "summary": summary_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        save_local_data(data)

def get_session_summary(user_id):
    if MONGO_AVAILABLE:
        doc = collection.find_one({"user_id": user_id})
        return doc.get("session_summaries", []) if doc else []
    else:
        data = load_local_data()
        return data.get(user_id, {}).get("session_summaries", [])

def update_habits(user_id, habits_text):
    if MONGO_AVAILABLE:
        collection.update_one({"user_id": user_id}, {"$set": {"habits_summary": habits_text}}, upsert=True)
    else:
        data = load_local_data()
        if user_id not in data:
            data[user_id] = {}
        data[user_id]["habits_summary"] = habits_text
        save_local_data(data)

def get_habits(user_id):
    doc = get_conversation(user_id)
    return doc.get("habits_summary") or "User is new to wellness tracking."

def make_audio_filename(user_id, role="ai"):
    uid = uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"{user_id}_{role}_{timestamp}_{uid}.mp3"
    return os.path.join(AUDIO_CACHE_DIR, filename)

def update_mood_history(user_id, mood, emotion):
    if MONGO_AVAILABLE:
        collection.update_one(
            {"user_id": user_id},
            {"$push": {"mood_history": {"mood": mood, "emotion": emotion, "timestamp": datetime.now(timezone.utc)}}},
            upsert=True
        )
    else:
        data = load_local_data()
        if user_id not in data:
            data[user_id] = {}
        data[user_id].setdefault("mood_history", []).append({
            "mood": mood,
            "emotion": emotion,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        save_local_data(data)

def get_mood_history(user_id):
    if MONGO_AVAILABLE:
        doc = collection.find_one({"user_id": user_id})
        return doc.get("mood_history", []) if doc else []
    else:
        data = load_local_data()
        return data.get(user_id, {}).get("mood_history", [])

def get_user_profile(user_id):
    doc = get_conversation(user_id)
    profile = doc.get("profile", {})
    if not profile:
        profile = {
            "name": user_id,
            "age": 0,
            "preferences": {"language": "English", "tone": "neutral"},
            "habits_summary": ""
        }
    profile.setdefault("preferences", {})
    profile["preferences"].setdefault("language", "English")
    profile["preferences"].setdefault("tone", "neutral")
    profile.setdefault("habits_summary", "User is new to wellness tracking.")
    return profile

def update_user_profile(user_id, profile):
    if MONGO_AVAILABLE:
        collection.update_one({"user_id": user_id}, {"$set": {"profile": profile}}, upsert=True)
    else:
        data = load_local_data()
        if user_id not in data:
            data[user_id] = {}
        data[user_id]["profile"] = profile
        save_local_data(data)

def add_goal(user_id, goal_text):
    goal_id = str(uuid.uuid4())
    goal = {"goal_id": goal_id, "text": goal_text, "progress": "Not Started"}
    if MONGO_AVAILABLE:
        collection.update_one({"user_id": user_id}, {"$push": {"goals": goal}}, upsert=True)
    else:
        data = load_local_data()
        if user_id not in data:
            data[user_id] = {}
        data[user_id].setdefault("goals", []).append(goal)
        save_local_data(data)

def update_goal_progress(user_id, goal_id, progress):
    if MONGO_AVAILABLE:
        collection.update_one({"user_id": user_id, "goals.goal_id": goal_id}, {"$set": {"goals.$.progress": progress}})
    else:
        data = load_local_data()
        if user_id in data:
            for goal in data[user_id].get("goals", []):
                if goal["goal_id"] == goal_id:
                    goal["progress"] = progress
            save_local_data(data)

def get_goals(user_id):
    doc = get_conversation(user_id)
    return doc.get("goals", [])

def get_daily_tip(profile=None):
    try:
        with open("daily_tips.json", "r", encoding="utf-8") as f:
            tips = json.load(f)
        if not tips:
            return translate_text("Remember to take a deep breath and smile 🙂.", profile.get("preferences", {}).get("language", "en") if profile else "en")
        if profile:
            tone = profile.get("preferences", {}).get("tone")
            if tone:
                filtered_tips = [t for t in tips if t.get("tone") == tone]
                if filtered_tips:
                    tips = filtered_tips
        selected_tip = random.choice(tips).get("tip", "Remember to take a deep breath and smile 🙂.")
        language_code = profile.get("preferences", {}).get("language", "en") if profile else "en"
        return translate_text(selected_tip, language_code)
    except Exception as e:
        print(f"Error loading daily tips: {e}")
        return translate_text("Remember to take a deep breath and smile 🙂.", profile.get("preferences", {}).get("language", "en") if profile else "en")

def get_guided_exercises(emotion, profile=None):
    try:
        with open("resources.json", "r", encoding="utf-8") as f:
            resources = json.load(f)
        exercises = resources.get(emotion, {}).get("exercises", []).copy()
        if profile:
            tone = profile.get("preferences", {}).get("tone", "")
            language_code = profile.get("preferences", {}).get("language", "en")
            if tone == "encouraging":
                exercises.append("Try a 5-minute power breathing exercise for positivity!")
            if language_code.lower() != "en":
                exercises = [translate_text(ex, language_code) for ex in exercises]
        return exercises
    except Exception as e:
        print(f"Error loading exercises: {e}")
        return []

def get_resources(emotion, profile=None):
    try:
        with open("resources.json", "r", encoding="utf-8") as f:
            resources = json.load(f)
        links = resources.get(emotion, {}).get("links", []).copy()
        if profile:
            tone = profile.get("preferences", {}).get("tone", "")
            language_code = profile.get("preferences", {}).get("language", "en")
            if tone == "supportive":
                links.append({"title": "Supportive Mental Health Article", "url": "https://example.com/support"})
            if language_code.lower() != "en":
                for link in links:
                    link["title"] = translate_text(link["title"], language_code)
        return links
    except Exception as e:
        print(f"Error loading resources: {e}")
        return []

def get_all_profiles():
    if MONGO_AVAILABLE:
        profiles_cursor = collection.find({}, {"user_id": 1, "last_updated": 1}).sort("last_updated", -1)
        return [doc["user_id"] for doc in profiles_cursor]
    else:
        data = load_local_data()
        profiles_with_time = []
        for uid, val in data.items():
            last_updated_str = val.get("last_updated")
            last_updated = datetime.min.replace(tzinfo=timezone.utc)
            if last_updated_str:
                try:
                    last_updated = datetime.fromisoformat(last_updated_str)
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            profiles_with_time.append((uid, last_updated))
        profiles_with_time.sort(key=lambda x: x[1], reverse=True)
        return [uid for uid, _ in profiles_with_time]

def create_profile(profile_name):
    if MONGO_AVAILABLE:
        if not collection.find_one({"user_id": profile_name}):
            collection.insert_one({
                "user_id": profile_name,
                "conversation": [],
                "profile": {"name": profile_name, "preferences": {"language": "English", "tone": "neutral"}},
                "last_updated": datetime.now(timezone.utc)
            })
    else:
        data = load_local_data()
        if profile_name not in data:
            data[profile_name] = {
                "conversation": [],
                "profile": {"name": profile_name, "preferences": {"language": "English", "tone": "neutral"}},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            save_local_data(data)
