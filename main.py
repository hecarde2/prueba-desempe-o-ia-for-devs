import os
import socket
from multiprocessing import Process

from backend.bot import TelegramRAGBot
from backend.config import TELEGRAM_BOT_TOKEN
from backend.rag_engine import RAGEngine
from backend.web_app import create_app


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
    if not rag_engine.raw_documents:
        print("Advertencia: No se encontraron documentos en docs/knowledge/. La base de conocimiento está vacía. Verifica docs/knowledge/base_conocimiento.md")
    else:
        print(f"Base de conocimiento cargada: {len(rag_engine.raw_documents)} documento(s).")
        if rag_engine.vector_store:
            print("Vector store (FAISS + Gemini embeddings) inicializado correctamente.")
        else:
            print("Vector store no disponible, modo offline activo.")

    web_app = create_app(rag_engine)
    try:
        preferred_port = int(os.getenv("PORT", "5002"))
    except ValueError:
        preferred_port = 5002
    port = get_available_port(preferred_port)

    if TELEGRAM_BOT_TOKEN:
        try:
            bot = TelegramRAGBot(rag_engine=rag_engine)
            process = Process(target=bot.run, daemon=True)
            process.start()
            print("Bot de Telegram arrancado en segundo plano.")
        except Exception as exc:
            print(f"No se pudo iniciar el bot de Telegram: {exc}")
    else:
        print("Telegram deshabilitado: no hay TELEGRAM_BOT_TOKEN definido.")

    print(f"Interfaz web disponible en http://localhost:{port}")
    try:
        web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nAplicación detenida por el usuario.")
    except Exception as exc:
        print(f"Error al iniciar la aplicación web: {exc}")
        raise


if __name__ == "__main__":
    main()
