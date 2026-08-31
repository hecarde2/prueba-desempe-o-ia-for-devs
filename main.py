import os
import socket
from multiprocessing import Process

from src.bot import TelegramRAGBot
from src.config import TELEGRAM_BOT_TOKEN
from src.rag_engine import RAGEngine
from src.web_app import create_app


def get_available_port(preferred_port: int, start_range: int = 5000, end_range: int = 65535) -> int:
    for port in range(preferred_port, end_range + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue

    for port in range(start_range, preferred_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue

    raise RuntimeError("No se encontró un puerto libre para iniciar la aplicación.")


def main():
    rag_engine = RAGEngine()
    web_app = create_app(rag_engine)
    preferred_port = int(os.getenv("PORT", "5002"))
    port = get_available_port(preferred_port)

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
