import os
import re

from flask import Flask, jsonify, request, render_template

from src.rag_engine import RAGEngine


def create_app(rag_engine: RAGEngine | None = None):
    app = Flask(__name__, template_folder="../templates")
    app.config["JSON_SORT_KEYS"] = False

    rag = rag_engine or RAGEngine()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/info")
    def info():
        md_path = os.path.join(os.path.dirname(__file__), "..", "documents", "base_conocimiento.md")
        items = []

        try:
            with open(md_path, "r", encoding="utf-8") as fh:
                content = fh.read()

            course_names = re.findall(r"^###\s+(.+)$", content, flags=re.MULTILINE)
            prices = re.findall(r"\*\*\s*([^*]+?)\s*\*\*\s*\|\s*\$(\d+)\s*USD", content)
            support = re.findall(r"\*\*Atención a Estudiantes y Soporte:\*\*\s*`([^`]+)`", content)
            admisiones = re.findall(r"\*\*Ventas, Becas y Admisiones:\*\*\s*`([^`]+)`", content)
            horarios = re.findall(r"\*\*Horarios de Atención Directa:\*\*\s*\*\*([^*]+)\*\*", content)

            if course_names:
                items.append({"label": "Cursos", "value": ", ".join(course_names[:3])})
            if prices:
                price_text = ", ".join(f"{name}: ${amount} USD" for name, amount in prices[:3])
                items.append({"label": "Precio", "value": price_text})
            if support:
                items.append({"label": "Soporte", "value": support[0]})
            if admisiones:
                items.append({"label": "Admisiones", "value": admisiones[0]})
            if horarios:
                items.append({"label": "Horario", "value": horarios[0]})
        except Exception:
            items = [
                {"label": "Cursos", "value": "Bots con Telegram e IA · Python · Prompt Engineering"},
                {"label": "Precio", "value": "$150 USD · $280 USD · $160 USD"},
                {"label": "Soporte", "value": "soporte@academiatech.com"},
                {"label": "Admisiones", "value": "admisiones@academiatech.com"},
                {"label": "Horario", "value": "Lun-Vie 8:00-18:00 GMT-5"},
            ]

        return jsonify({"items": items})

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
