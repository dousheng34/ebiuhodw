"""Configuration and environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# SheerID
SHEERID_ACCESS_TOKEN = os.getenv("SHEERID_ACCESS_TOKEN", "")
SHEERID_BASE_URL = "https://services.sheerid.com/rest/v2"

SHEERID_PROGRAM_IDS = {
    "student": os.getenv("SHEERID_PROGRAM_ID_STUDENT", ""),
    "military": os.getenv("SHEERID_PROGRAM_ID_MILITARY", ""),
    "teacher": os.getenv("SHEERID_PROGRAM_ID_TEACHER", ""),
    "first_responder": os.getenv("SHEERID_PROGRAM_ID_FIRST_RESPONDER", ""),
}

# GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "username/sheerpro-data")
GITHUB_DATA_FILE = "verifications.json"

# Server
PORT = int(os.getenv("PORT", "8080"))

# Verification type labels
VERIFICATION_TYPES = {
    "student": "🎓 Student",
    "military": "🪖 Military",
    "teacher": "👨‍🏫 Teacher",
    "first_responder": "🚒 First Responder",
}

# Fields required per verification type
REQUIRED_FIELDS = {
    "student": ["first_name", "last_name", "birth_date", "school_name", "email"],
    "military": ["first_name", "last_name", "birth_date", "status"],
    "teacher": ["first_name", "last_name", "birth_date", "school_name", "email"],
    "first_responder": ["first_name", "last_name", "birth_date", "organization"],
}

FIELD_PROMPTS = {
    "first_name": "👤 Enter your *First Name*:",
    "last_name": "👤 Enter your *Last Name*:",
    "birth_date": "📅 Enter your *Date of Birth* (format: YYYY-MM-DD, e.g. 1998-06-15):",
    "school_name": "🏫 Enter your *School / University Name*:",
    "organization": "🏢 Enter your *Organization Name*:",
    "email": "📧 Enter your *Email Address* (school/work email preferred):",
    "status": "🪖 Enter your *Military Status*:\n(ACTIVE_DUTY / RESERVIST / VETERAN / RETIREE / MILITARY_FAMILY)",
}
