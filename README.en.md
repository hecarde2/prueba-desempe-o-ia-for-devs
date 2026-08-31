# AI Academic Support Assistant

This application combines a web interface, a Telegram bot, and an RAG engine to answer questions about courses, pricing, enrollments, refunds, and support for an academy.

It works with two layers:
- a Gemini-powered layer when the API key and quota are available
- a local fallback layer based on the business knowledge base, which keeps the app working even if external services fail or are unavailable

## Goal

- Answer only with information from the business knowledge base.
- Escalate questions outside the supported scope.
- Keep the app operational even when Gemini is down, over quota, or using an unsupported model.
- Support both web and Telegram interfaces in a single project.

## Tech Stack

- Python 3.10+
- Flask for the web interface
- python-telegram-bot for Telegram
- LangChain and FAISS for RAG
- Google Gemini for LLM and embeddings
- Markdown and local knowledge files in documents/

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── .env
├── README.md
├── README.en.md
├── documents/
│   └── base_conocimiento.md
├── src/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   ├── rag_engine.py
│   └── web_app.py
└── templates/
    └── index.html
```

## Prerequisites

- Python 3.10 or newer
- Recommended virtual environment
- Telegram bot token generated with @BotFather
- Google Gemini API key from Google AI Studio

## Configuration

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create the environment file:

```bash
cp .env.example .env
```

4. Fill in the variables in `.env`:

```env
TELEGRAM_BOT_TOKEN=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=0
```

Important notes:
- Do not hardcode any API keys in the source code.
- `HUMAN_AGENT_CHAT_ID` must be the chat ID for the human support agent.
- If `TELEGRAM_BOT_TOKEN` is missing, the app runs the web interface but not the Telegram bot.

## Running the app

From the project root:

```bash
source venv/bin/activate
python main.py
```

You can also force a port explicitly:

```bash
PORT=5010 python main.py
```

The app automatically picks a free port if the preferred one is already occupied.

## How it works

1. Loads the knowledge base from the documents folder.
2. Searches for relevant context using similarity retrieval.
3. Tries Gemini when the API is available and the account has quota.
4. Falls back to the local business knowledge base if Gemini is unavailable, over quota, or using an unsupported model.
5. Escalates to a human agent when the question is outside the scope or the documentation does not provide an answer.

## Grounding rules

- Answers must be based only on the local business documents.
- If the information is not explicitly present in the knowledge base, the assistant should escalate instead of guessing.
- The app keeps a concise, natural Spanish tone while staying business-grounded.

## Security

- `.env` must not be committed to the repository.
- Keys are loaded through environment variables.
- Secrets are not embedded in the source code or logs.

## Verification performed

This project was validated in real execution to confirm that:
- the web app responds correctly
- the Telegram bot starts without breaking the app
- the local fallback works when Gemini is unavailable
- the application does not crash on API quota or model compatibility errors

## Access URL

After startup, the interface is available at:

```text
http://localhost:5010
```

If port 5010 is busy, the app will attempt another free port automatically.
