# Project Documentation

## Overview

This project develops an AI support assistant for an academy using document-based retrieval and artificial intelligence. The solution combines:

- a web interface built with Flask
- a Telegram bot
- a RAG engine (Retrieval-Augmented Generation)
- Gemini integration when the account has available quota
- a local fallback layer using the business knowledge base to prevent critical failures

The goal is to answer questions about courses, prices, requirements, enrollment, refund policies, and support using the internal documentation of the business.

## Objective

- Reply to customer queries with real and verifiable information.
- Avoid fabricated or out-of-context answers.
- Escalate questions outside the supported scope to a human advisor.
- Keep the application operational even when the external API fails.

## Architecture

### 1. Web interface
The web application is built with Flask and provides a chat interface for the assistant. It also includes a fixed info bar populated from the local knowledge file.

### 2. Telegram bot
The bot uses python-telegram-bot to listen for incoming messages and respond through Telegram. It can also escalate a query to a human chat if needed.

### 3. RAG engine
The main logic is implemented in `src/rag_engine.py`.

The process is:

1. Load documents from `documents/`
2. Split the content into chunks
3. Build a vector index with FAISS
4. Search for relevant context based on the user question
5. Try to answer with Gemini when available
6. Use the local fallback when Gemini fails or quota is exhausted

### 4. Knowledge base
The primary source is:

- `documents/base_conocimiento.md`

This file contains the business information used to answer customer queries and to populate the local info bar in the visual interface.

## Project structure

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── .env
├── README.md
├── README.en.md
├── DOCUMENTACION_PROYECTO.md
├── DOCUMENTACION_PROYECTO_EN.md
├── documents/
│   └── base_conocimiento.md
├── src/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   ├── rag_engine.py
│   └── web_app.py
├── templates/
│   └── index.html
└── venv/
```

## Environment configuration

Environment variables are used to avoid hardcoding secrets in the code.

Base file:

- `.env.example`

Variables:

```env
TELEGRAM_BOT_TOKEN=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=0
```

### Variable descriptions

- `TELEGRAM_BOT_TOKEN`: token for the Telegram bot generated through BotFather.
- `GOOGLE_API_KEY`: key for Google Gemini.
- `GEMINI_MODEL`: chat model used by the application.
- `GEMINI_EMBEDDING_MODEL`: embedding model for the vector database.
- `HUMAN_AGENT_CHAT_ID`: chat ID for the human support agent used in escalations.

## Installation

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the .env file

```bash
cp .env.example .env
```

Then fill in the real credentials.

## Execution

### Run the app

```bash
python main.py
```

### Run with a specific port

```bash
PORT=5010 python main.py
```

The app detects a free port automatically if the preferred one is already occupied.

## System behavior

### Document-based responses
The assistant logic requires answers to be based only on the available business knowledge base.

If a question is not supported by the documentation, the app does not invent information and escalates instead.

### Human escalation
When a query is outside scope or there is not enough documentation, the app returns an escalation response and, if configured, notifies the human agent through Telegram.

### Local fallback
Even when Gemini is available, the app may fail because of:

- exhausted quota
- unsupported model
- authentication issues
- temporary external service failure

In those cases, it uses local documentation to keep the app working without crashing.

## Security

- API keys must not be hardcoded into the source code.
- The `.env` file should never be committed to the repository.
- Secrets must only be handled through environment variables.

## Validation performed

The project was validated in real execution and confirmed that:

- the app starts without crashing because of port conflicts
- the web interface responds correctly
- the local info API responds with data from the Markdown file
- the Telegram bot starts and responds with `getUpdates 200 OK`
- the app keeps working even when Gemini errors or quota is exhausted

## Main use cases

- What courses are available?
- How much does each course cost?
- What is the enrollment process?
- Are there refund policies?
- How can I contact support?
- What prerequisites are needed?

## Known limitations

- Gemini responses depend on the available quota in the account.
- If the model is no longer supported or the key lacks access, the app uses the local knowledge base as backup.
- The web app runs on Flask and is intended for local or simple deployment, not as a production WSGI server without an appropriate host like gunicorn.

## Deliverable summary

This project was developed as a functional deliverable including:

- web chat
- Telegram support
- local RAG system
- Gemini integration
- human escalation
- stable documentation and execution flow
