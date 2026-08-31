# AI Customer Support Bot (Telegram + Gemini RAG)

An automated customer support Telegram bot using **RAG (Retrieval-Augmented Generation)** to answer questions about courses, pricing, enrollments, and refunds for an academy, with the ability to escalate unanswered queries to a human agent.

## Tech Stack

- **Python** 3.10+
- **Telegram** — bot interface via `python-telegram-bot`
- **LangChain** — RAG flow orchestration
- **FAISS** — vector database for context retrieval
- **Google Gemini** — embeddings (`text-embedding-004`) and LLM (`gemini-1.5-flash`)
- **PyPDF** — PDF document parsing

## Architecture

1. **Telegram Interface**: built with `python-telegram-bot` in polling mode.
2. **RAG Core**: loads documents from `documents/`, splits them into chunks, and builds a FAISS index using Gemini embeddings.
3. **LLM**: `gemini-1.5-flash` with low temperature (0.1), strict grounding rules, and few-shot examples.
4. **Caching Layer**: an in-memory dictionary caches repeated queries to optimize API usage and response times.
5. **Human Escalation**: when a question cannot be answered from the available context, a human agent is notified via Telegram.

## Project Structure

```
.
├── main.py                      # Entry point (starts the bot)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── .gitignore                   # Files excluded from version control
├── documents/                   # Knowledge base
│   └── base_conocimiento.md
└── src/
    ├── __init__.py              # Marks `src/` as a Python package
    ├── config.py                # Loads and validates environment variables
    ├── bot.py                   # Telegram bot logic
    └── rag_engine.py            # RAG pipeline (documents, vectors, LLM)
```

## Prerequisites

- Python 3.10 or higher
- Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/))
- Telegram bot token (obtained via [@BotFather](https://t.me/BotFather))

## Installation

1. **Clone the repository and install dependencies** (a virtual environment is recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate        # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in your credentials:

   | Variable | Description |
   | :--- | :--- |
   | `TELEGRAM_BOT_TOKEN` | Your bot token (from @BotFather) |
   | `GOOGLE_API_KEY` | Google Gemini API key |
   | `HUMAN_AGENT_CHAT_ID` | Telegram chat ID of the human agent |

3. **Add the knowledge base**: place your documents in the `documents/` folder. Supported formats are **PDF**, **Markdown (`.md`)**, and **text (`.txt`)**.

4. **Run the application**:

   ```bash
   python main.py
   ```

## Grounding & Escalation Rules

- Low LLM temperature (`0.1`) minimizes hallucination risks.
- If the answer is not explicitly present in the knowledge base, the bot replies with `ESCALATE_TO_HUMAN`.
- The system automatically forwards the unanswered query to the human agent's chat defined in `HUMAN_AGENT_CHAT_ID`.

## Security Notes

- **Never** commit your `.env` file to the repository. It contains sensitive credentials.
- The `.gitignore` already excludes `.env`, `venv/`, and `__pycache__/`.
- If a key was ever exposed publicly, revoke it and generate a new one immediately.
