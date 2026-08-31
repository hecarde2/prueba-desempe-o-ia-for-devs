import os
from dotenv import load_dotenv

load_dotenv()


def _get_optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


TELEGRAM_BOT_TOKEN = _get_optional("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = _get_optional("GOOGLE_API_KEY")
GEMINI_MODEL = _get_optional("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_EMBEDDING_MODEL = _get_optional("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
HUMAN_AGENT_CHAT_ID = int(_get_optional("HUMAN_AGENT_CHAT_ID", "0") or 0)
