import os
import re

from flask import Flask, jsonify, request, render_template

from backend.config import TELEGRAM_BOT_TOKEN
from backend.rag_engine import RAGEngine


def create_app(rag_engine: RAGEngine | None = None):
    # Frontend está en frontend/templates, backend en backend/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "frontend", "templates")
    static_dir = os.path.join(base_dir, "frontend", "static")
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config["JSON_SORT_KEYS"] = False

    rag = rag_engine or RAGEngine()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/info")
    def info():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Soporta nueva ruta docs/knowledge y legacy documents/
        candidates = [
            os.path.join(base_dir, "docs", "knowledge", "base_conocimiento.md"),
            os.path.join(base_dir, "documents", "base_conocimiento.md"),
            os.path.join(os.path.dirname(__file__), "..", "documents", "base_conocimiento.md"),
        ]
        md_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
        items = []

        try:
            with open(md_path, "r", encoding="utf-8") as fh:
                content = fh.read()

            course_names = re.findall(r"^###\s+(.+)$", content, flags=re.MULTILINE)
            prices = re.findall(r"\*\*\s*([^*]+?)\s*\*\*\s*\|\s*\$(\d+)\s*USD", content)
            support = re.findall(r"\*\*Atención a Estudiantes y Soporte:\*\*\s*`([^`]+)`", content)
            admisiones = re.findall(r"\*\*Ventas, Becas y Admisiones:\*\*\s*`([^`]+)`", content)
            horarios = re.findall(r"Atención Administrativa y Soporte:\*\*\s*([^\n]+)", content)
            # fallback: try Horarios de Atención Directa header
            if not horarios:
                horarios = re.findall(r"Horarios de Atención Directa[^\n]*\n[^\n]*?(\bLunes a Viernes[^\n]+)", content)

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
                # limpiar markdown y espacios
                horario_clean = horarios[0].strip().strip("*").strip()
                items.append({"label": "Horario", "value": horario_clean})
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
            "telegram_enabled": bool(TELEGRAM_BOT_TOKEN),
            "rag_ready": bool(rag and len(getattr(rag, "raw_documents", [])) > 0),
            "vector_store_ready": bool(rag and getattr(rag, "vector_store", None) is not None),
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
