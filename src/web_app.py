from flask import Flask, jsonify, request, render_template

from src.rag_engine import RAGEngine


def create_app(rag_engine: RAGEngine | None = None):
    app = Flask(__name__, template_folder="../templates")
    app.config["JSON_SORT_KEYS"] = False

    rag = rag_engine or RAGEngine()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def status():
        return jsonify({
            "status": "ok",
            "name": "Sora AI Support",
            "telegram_enabled": bool(rag and getattr(rag, "vector_store", None) is not None),
        })

    @app.route("/api/chat", methods=["POST"])
    def chat():
        payload = request.get_json(silent=True) or {}
        question = (payload.get("message") or "").strip()

        if not question:
            return jsonify({"error": "Escribe una pregunta antes de enviar."}), 400

        result = rag.query(question)
        return jsonify({
            "answer": result.get("message", "No tengo una respuesta disponible."),
            "action": result.get("action", "reply"),
            "mode": result.get("mode", "offline"),
        })

    return app
