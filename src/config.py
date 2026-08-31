import os
from dotenv import load_dotenv

load_dotenv()


def _get_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"La variable de entorno requerida '{name}' no está definida. Copia .env.example a .env y configúrala.")
    return value


TELEGRAM_BOT_TOKEN = _get_required("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = _get_required("GOOGLE_API_KEY")
HUMAN_AGENT_CHAT_ID = int(_get_required("HUMAN_AGENT_CHAT_ID"))
