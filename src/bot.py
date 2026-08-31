import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from src.rag_engine import RAGEngine
from src.config import TELEGRAM_BOT_TOKEN, HUMAN_AGENT_CHAT_ID

logging.basicConfig(level=logging.INFO)


class TelegramRAGBot:
    def __init__(self, rag_engine: RAGEngine | None = None):
        self.rag_engine = rag_engine or RAGEngine()
        self.human_agent_id = HUMAN_AGENT_CHAT_ID
        self.token = TELEGRAM_BOT_TOKEN

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "¡Hola! 👋 Soy Sora, la asistente virtual de la Academia de Tecnología e IA.\n"
            "¿En qué te puedo ayudar hoy sobre cursos, horarios, precios, inscripciones o reembolsos?"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        chat_id = update.message.chat_id
        username = update.message.from_user.username or update.message.from_user.first_name

        result = self.rag_engine.query(user_text)

        await update.message.reply_text(result["message"])

        if result["action"] == "escalate" and self.human_agent_id:
            escalation_msg = (
                f"⚠️ *Escalamiento Requerido*\n"
                f"Usuario: @{username} (ID: `{chat_id}`)\n"
                f"Consulta: {user_text}"
            )
            await context.bot.send_message(
                chat_id=self.human_agent_id,
                text=escalation_msg,
                parse_mode="Markdown"
            )

    def run(self):
        if not self.token:
            print("Telegram deshabilitado: faltan las credenciales de TELEGRAM_BOT_TOKEN.")
            return False

        asyncio.set_event_loop(asyncio.new_event_loop())
        app = ApplicationBuilder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        print("Bot de Telegram iniciado exitosamente...")
        app.run_polling()
        return True
