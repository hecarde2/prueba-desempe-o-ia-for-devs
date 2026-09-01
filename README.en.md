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

## Installation and Setup

### 1. Create a virtual environment:

```bash
python3 -m venv venv
```

### 2. Activate the virtual environment:

**On Linux/Mac:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 3. Install dependencies:

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables:

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
TELEGRAM_BOT_TOKEN=your_token_here
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=your_chat_id
```

**Important notes:**
- Never hardcode API keys in the source code, always use environment variables.
- `HUMAN_AGENT_CHAT_ID` must be your Telegram user ID (where out-of-scope queries will be escalated).
- If `TELEGRAM_BOT_TOKEN` is not set, the app will run only the web interface.

## Running the app

**Make sure you are in the project directory and the virtual environment is activated.**

From the project root:

```bash
python main.py
```

To specify a custom port:

```bash
PORT=5000 python main.py
```

The app automatically detects and uses a free port if the preferred one is already in use.

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

## Accessing the application

After running `python main.py`, the web interface will be available at:

```text
http://localhost:5002
```

(If port 5002 is busy, the app will automatically choose another free port and display it in the console)

You can also access it from another machine using your server's IP:

```text
http://<your_ip>:5002
```

**For Telegram:** The bot will be active automatically if you configured `TELEGRAM_BOT_TOKEN`.
