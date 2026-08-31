import os
from multiprocessing import Process

from src.bot import TelegramRAGBot
from src.config import TELEGRAM_BOT_TOKEN
from src.rag_engine import RAGEngine
from src.web_app import create_app


def main():
    rag_engine = RAGEngine()
    web_app = create_app(rag_engine)
    port = int(os.getenv("PORT", "5002"))

    if TELEGRAM_BOT_TOKEN:
        bot = TelegramRAGBot(rag_engine=rag_engine)
        process = Process(target=bot.run, daemon=True)
        process.start()
        print("Bot de Telegram arrancado en segundo plano.")
    else:
        print("Telegram deshabilitado: no hay TELEGRAM_BOT_TOKEN definido.")

    print(f"Interfaz web disponible en http://localhost:{port}")
    web_app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
