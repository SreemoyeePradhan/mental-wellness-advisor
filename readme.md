# 🧘 Mental Wellness AI Advisor

## Description

Mental Wellness AI Advisor is an interactive, multi-profile, multilingual assistant built with **Streamlit** that supports mental wellness by detecting moods and emotions from user messages, providing personalized guidance, tracking habits and goals, and offering daily tips and exercises. It uses AI-based conversation, translation, and sentiment analysis to create a supportive wellness environment.

---

## Features

- Multi-profile creation and selection.
- Mood and emotion detection from user messages with emoji feedback.
- Persistent conversation logging using MongoDB or local JSON storage fallback.
- User profile management with language and tone preferences.
- Habits and goals tracking with progress updates.
- AI-generated session summaries.
- Daily wellness tips based on mood and tone preferences.
- Guided exercises and resources personalized to the user’s emotional state.
- Multilingual support (English, Hindi, Spanish, French, German).
- Light and dark theme support.
- Voice synthesis for AI responses.

---

## Tools and Technologies Used

- **Python** – Backend programming.
- **Streamlit** – Web application frontend.
- **VADER Sentiment Analyzer** – Mood and emotion detection.
- **deep_translator** – Multilingual translation.
- **pymongo** – MongoDB integration for persistent storage.
- **uuid, datetime** – Unique IDs and timestamps.
- **dotenv** – Environment variable management.
- **JSON** – Local storage fallback.
- **Google Translator API** – Translation of UI and responses.

---

## Further Enhancements

- Support additional languages for broader accessibility.
- Add AI-based habit and goal suggestions for personalized wellness plans.
- Implement caching for translations to improve performance.
- Visualize mood history and sentiment trends over time.
- Add analytics for wellness patterns and progress tracking.
- Integrate more interactive voice commands for a conversational AI experience.
