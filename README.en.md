# Sora AI Assistant — Academic Support

> **Academy of Technology & AI** · Support bot that answers *only* with official business information. Combines **Flask web + Telegram bot + RAG engine (FAISS + Gemini)** with a **fully offline fallback** that keeps the app alive when Gemini is out of quota, uses an unavailable model, or has no credentials.

Two layers alternate automatically:
1. **Smart layer (Gemini)**: when `GOOGLE_API_KEY` is valid and quota remains, uses `gemini-embedding-001` embeddings + LLM `gemini-2.5-flash-lite` / `gemini-3.6-flash` with context.
2. **Local layer (offline)**: on any API failure, searches `docs/knowledge/base_conocimiento.md` with token + alias matching and answers without hallucinating. With no evidence, it escalates to a human.

---

## Table of Contents
1. [Quick start](#quick-start-60-seconds)
2. [Prerequisites](#prerequisites)
3. [Project structure](#project-structure)
4. [Step-by-step setup](#step-by-step-setup)
5. [Environment variables](#environment-variables)
6. [Running](#running)
7. [How to use (real examples)](#how-to-use-real-examples)
8. [How it works](#how-it-works)
9. [Backend API](#backend-api)
10. [RAG engine in detail](#rag-engine-in-detail)
11. [Business rules](#business-rules)
12. [Security](#security)
13. [Verification & tests](#verification--tests)
14. [Troubleshooting](#troubleshooting)
15. [Credits & deliverable](#credits--deliverable)

---

## Quick start (60 seconds)

```bash
# 1. Clone / unzip and enter
cd "prueba-desempe-o-ia-for-devs (entrega)"

# 2. Env + deps
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Credentials
cp .env.example .env
nano .env                       # fill TELEGRAM_BOT_TOKEN and GOOGLE_API_KEY

# 4. Run
python main.py
# Open http://localhost:5002  (if 5002 is busy, the app picks the next free port and prints it)
```

> If `TELEGRAM_BOT_TOKEN` is empty the web still works and the bot is simply disabled.

---

## Prerequisites

| Requirement | Version / Detail | Where to get it |
|-------------|------------------|-----------------|
| Python | **3.10+** (tested on **3.12.3**) | `python3 --version` |
| pip | bundled with Python | `pip --version` |
| Telegram token | Bot created with @BotFather | https://t.me/BotFather |
| Gemini API key | Google AI Studio | https://aistudio.google.com/app/apikey |
| Human chat ID | Your Telegram ID for escalations | See step 4.3 below |

**Main deps** (`requirements.txt`):
```
python-telegram-bot==21.1.1
Flask==3.0.3
langchain==0.1.20 · langchain-google-genai==1.0.3 · langchain-community==0.0.38
faiss-cpu==1.8.0 · pypdf==4.2.0 · python-dotenv==1.0.1
```
All compatible with Python 3.12 and verified with `pip check`.

---

## Project structure (junior-friendly — clearly separated)

> **Goal:** a junior finds in 5 seconds where everything is: `backend` = server, `frontend` = visuals, `docs` = papers.

```text
.
├── main.py                     # ← entry point (from root: python main.py)
├── requirements.txt            # deps (Flask, telegram-bot, langchain, faiss...)
├── .env.example / .env         # template and your keys (not versioned)
├── README.md / README.en.md    # user guide (you are here)
│
├── backend/                    # 🔧 BACKEND — all Python server
│   ├── config.py               # reads .env → TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY...
│   ├── rag_engine.py           # RAG core 618 lines: FAISS + Gemini + offline + circuit-breaker
│   ├── web_app.py              # Flask 90 lines: /, /api/info, /api/status, /api/chat
│   ├── bot.py                  # Telegram 67 lines: /start + handle_message + escalation
│   └── __init__.py
│
├── frontend/                   # 🎨 FRONTEND — all visuals
│   ├── templates/
│   │   └── index.html          # HTML with Jinja2 (uses url_for to static)
│   └── static/
│       ├── css/
│       │   └── style.css       # 20KB — light/dark vars, sidebar, chat, responsive
│       └── js/
│           └── app.js          # 9KB — fetch /api/*, theme, font, sidebar, chat
│
└── docs/                       # 📚 DOCS — all written
    ├── README.md               # docs index
    ├── DOCUMENTACION_PROYECTO.md      # tech doc ES (516 lines, 20 sections)
    ├── DOCUMENTACION_PROYECTO_EN.md   # tech doc EN (515 lines)
    └── knowledge/
        └── base_conocimiento.md       # SINGLE source of truth (256 lines, 9 sections)
```

**Before vs now (so you see the change):**
- `src/` → `backend/` (clearer: backend = server)
- `templates/` → `frontend/templates/` + `frontend/static/` (separate CSS/JS)
- `documents/` → `docs/knowledge/` + `docs/DOCUMENTACION_*` (all writing together)

`docs/knowledge/base_conocimiento.md` holds **all** official information (courses, pricing, enrollment, policies, support, labs, mentoring, R&D) and is what the backend reads (`backend/rag_engine.py:87` and `backend/web_app.py:24` with fallback to `documents/` legacy).

---

## Step-by-step setup

### 1. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows PowerShell/CMD
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Copy environment variables

```bash
cp .env.example .env
```

### 3. Get each credential

#### 3.1 Telegram — `TELEGRAM_BOT_TOKEN`
1. Open Telegram → search `@BotFather` → `/newbot`.
2. Follow the wizard, pick name and username → copy token `123456:AAH...`.
3. Paste into `.env` as `TELEGRAM_BOT_TOKEN=123456:AAH...`.
4. *Optional:* if you skip this, the app runs web-only (see `backend/bot.py:44`).

#### 3.2 Google Gemini — `GOOGLE_API_KEY` + models
1. Go to https://aistudio.google.com/app/apikey → **Create API key**.
2. Copy key (`AIza...` or `AQ.Ab8...` depending on project) → `GOOGLE_API_KEY=...` in `.env`.
3. Default models (already configured, no need to change unless you want):
   ```env
   GEMINI_MODEL=gemini-2.5-flash-lite
   GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
   ```
   The code automatically falls back to `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-3.5-flash` if the primary fails or is out of quota (`backend/rag_engine.py:70`).

#### 3.3 Human for escalations — `HUMAN_AGENT_CHAT_ID`
1. On Telegram search `@userinfobot` → `/start` → copy your numeric ID.
2. In `.env` set `HUMAN_AGENT_CHAT_ID=123456789`.
3. When someone asks out-of-scope, the bot sends `⚠️ Escalamiento Requerido` to that chat (`backend/bot.py:33`).

### 4. Final `.env` example

```env
TELEGRAM_BOT_TOKEN=1234567890:AAH...your_token...
GOOGLE_API_KEY=AIza...your_key...
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=1301721795
PORT=5002
```

> `HUMAN_AGENT_CHAT_ID=0` disables human notifications. `PORT` is optional.

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | No | `""` | Token from @BotFather. If empty, bot does not start but web does (`main.py:40`). |
| `GOOGLE_API_KEY` | No | `""` | Gemini key. If missing, FAISS is not initialized and everything goes offline (`backend/rag_engine.py:85`). |
| `GEMINI_MODEL` | No | `gemini-2.5-flash-lite` | Chat model. Fallback list in `GEMINI_CHAT_MODELS`. |
| `GEMINI_EMBEDDING_MODEL` | No | `models/gemini-embedding-001` | Embedding model. Fallback `models/gemini-embedding-2`. |
| `HUMAN_AGENT_CHAT_ID` | No | `0` | Numeric advisor ID. Use `@userinfobot`. |
| `PORT` | No | `5002` | Preferred port. `get_available_port()` (`main.py:11`) probes up to 65535. |

Never hardcode keys: they are loaded via `python-dotenv` in `backend/config.py:4`.

---

## Running

### Option A — Web + Telegram together (recommended)

```bash
python main.py
```

Expected output:
```
Base de conocimiento cargada: 1 documento(s).
Vector store (FAISS + Gemini embeddings) inicializado correctamente.
Bot de Telegram arrancado en segundo plano.
Interfaz web disponible en http://localhost:5002
 * Running on http://0.0.0.0:5002
```

Open `http://localhost:5002` and chat with Sora. If you configured the bot, open Telegram and send `/start`.

### Option B — Web only (no Telegram)

```bash
# Leave TELEGRAM_BOT_TOKEN empty in .env
python main.py
# → "Telegram deshabilitado: no hay TELEGRAM_BOT_TOKEN definido."
```

### Option C — Custom port

```bash
PORT=5000 python main.py
# or
PORT=5010 python main.py
```

If the port is busy, `main.py:11` tries the next one and prints it.

### Stop

`Ctrl+C` in the terminal. The bot process is `daemon=True` and ends with the web.

---

## How to use (real examples)

Try these in web or Telegram:

| Question | Expected answer | Source |
|----------|----------------|--------|
| `How much does the bots course cost?` / `¿Cuánto cuesta el curso de bots?` | `Bots con Telegram e IA: $150 USD | pronto pago $120 USD (until day 20) | 2 cuotas 2 x $75 USD` | Offline / Gemini |
| `Price of the python course?` | `$280 USD` + plans | Offline / Gemini |
| `cuanto cuesta?` (no course) | List of 3 regular prices | Offline |
| `How to get a refund?` / `¿Cómo pedir reembolso?` | `7 natural days → 100% no questions` | Offline |
| `What are the support hours?` / `¿Cuál es el horario de atención?` | `Mon-Fri 8:00-18:00 GMT-5. Sat 9:00-13:00` | Offline |
| `Requirements for the bots course?` | `Basic Python knowledge...` | Offline |
| `How long is the course?` | `4 weeks (20 lective hours ...)` | Offline |
| `Hello` / `Hola` | Sora greeting (does not escalate) | Offline |
| `Who is the president of France?` | `Sorry, out of scope... human advisor` + Telegram escalation | Offline `escalate` |

All offline answers were validated with `backend/rag_engine.py:_offline_response`.

---

## How it works

```
User (Web/Telegram)
        ↓
  ┌─────────────┐
  │  RAGEngine  │  backend/rag_engine.py:84
  │  1. Load docs/knowledge/*.md|pdf → TextLoader/PyPDFLoader
  │  2. Splitter 800/100 → RecursiveCharacterTextSplitter
  │  3. FAISS.from_documents(GoogleGenerativeAIEmbeddings)
  └─────────────┘
        ↓  similarity_search(k=3)
  ┌─────────────┐
  │   Gemini    │  ChatGoogleGenerativeAI(temperature=0.1)
  │  2-4 attempts │ GEMINI_CHAT_MODELS with fast-retry patch (1 attempt)
  │  + SYSTEM_PROMPT with ESCALATE_TO_HUMAN
  └─────────────┘
        ↓ on 429/quota/404/500 → 60s circuit-breaker
  ┌─────────────┐
  │ Offline     │  _offline_search (STOPWORDS + aliases) → _offline_response
  │  - price table parsed
  │  - hours via regex Mon-Fri
  │  - refund/enrollment/duration/certificate
  │  - best_matching_lines threshold 5
  └─────────────┘
        ↓
   Response {action: reply|escalate, mode: gemini|offline}
        ↓
  Web (/api/chat) or Telegram (reply + human notification)
```

**Web flow (`backend/web_app.py`):**
- `GET /` → `render_template("index.html")`
- `GET /api/info` → parses `base_conocimiento.md` with regex and returns 5 pills (Courses, Price, Support, Admissions, Hours)
- `GET /api/status` → `{status:ok, telegram_enabled: bool(TELEGRAM_BOT_TOKEN), rag_ready, vector_store_ready}`
- `POST /api/chat {message}` → `rag.query()` → `{answer, action, mode}`

**Telegram flow (`backend/bot.py`):**
- `CommandHandler("start")` → greeting
- `MessageHandler(TEXT)` → `rag.query()` → `reply_text` → if `escalate` and `HUMAN_AGENT_CHAT_ID` → `send_message` to human.

---

## Backend API

### `GET /`
HTML chat. `frontend/templates/index.html` does `fetch('/api/info')` and `fetch('/api/chat')`.

### `GET /api/info`
```bash
curl http://localhost:5002/api/info
```
```json
{
  "items": [
    {"label":"Cursos","value":"Curso 1: Desarrollo de Bots..., Curso 2: Python..., Curso 3: Prompt..."},
    {"label":"Precio","value":"Bots con Telegram e IA: $150 USD, Python para Data Science: $280 USD, Prompt Eng. y Agentes: $160 USD"},
    {"label":"Soporte","value":"soporte@academiatech.com"},
    {"label":"Admisiones","value":"admisiones@academiatech.com"},
    {"label":"Horario","value":"Lunes a Viernes de 8:00 AM a 6:00 PM (GMT-5). Sábados de 9:00 AM a 1:00 PM (GMT-5)."}
  ]
}
```

### `GET /api/status`
```bash
curl http://localhost:5002/api/status
```
```json
{"status":"ok","name":"Sora AI Support","telegram_enabled":true,"rag_ready":true,"vector_store_ready":true}
```

### `POST /api/chat`
```bash
curl -X POST http://localhost:5002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How much does the bots course cost?"}'
```
```json
{
  "answer":"Según la base de conocimiento: Bots con Telegram e IA: $150 USD | pronto pago $120 USD (hasta el 20) | 2 cuotas 2 x $75 USD.",
  "action":"reply",
  "mode":"offline"
}
# action = "escalate" when out-of-scope
# mode = "gemini" when Gemini answered, "offline" when local fallback answered
```

Validation error:
```bash
curl -X POST http://localhost:5002/api/chat -H "Content-Type: application/json" -d '{"message":""}'
# → 400 {"error":"Escribe una pregunta antes de enviar."}
```

---

## RAG engine in detail

**File:** `backend/rag_engine.py` (540 lines) — system core.

| Stage | Detail | Code |
|-------|--------|------|
| **Load** | Reads `docs/knowledge/` sorted; `.pdf` via `PyPDFLoader`, `.md/.txt` via `TextLoader(utf-8)` | `:_load_documents:94` |
| **Split** | `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)` | `:_init_vector_store:114` |
| **Embeddings** | `GoogleGenerativeAIEmbeddings` with fallback `gemini-embedding-001` → `gemini-embedding-2` | `:77` |
| **Vector store** | `FAISS.from_documents(chunks, embeddings)` | `:121` |
| **Search** | `similarity_search(k=3)` → context `"\n---\n".join(docs)` | `:494` |
| **LLM** | `ChatGoogleGenerativeAI(temperature=0.1, max_retries=0)` with `SYSTEM_PROMPT` forcing `ESCALATE_TO_HUMAN` if no evidence | `:500` |
| **Retry patch** | `_create_retry_decorator` → `stop_after_attempt(1)` so quota does not block 60s, immediate fallback | `:16` |
| **Circuit-breaker** | `_quota_blocked_until = now+60s` after 429 → next queries skip Gemini and go offline | `:87,526` |
| **Offline search** | Normalizes (NFKD no accents), filters `STOPWORDS` (el, la, de, que...), scores by tokens + `SEARCH_ALIASES` per category | `:_offline_search:140` |
| **Offline response** | Priority: prices (parsed table) → requirements → refund (7 days) → enrollment → duration → certificate → hours → content → modality → `best_matching_lines` threshold 5 → escalate if 0 overlap | `:_offline_response:254` |
| **Cache** | `dict` by normalized question | `:489` |

**Current models 2026** (verified with `genai.list_models()`): `gemini-2.5-flash-lite`, `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-3.5-flash`. Older `gemini-1.5-flash` and `text-embedding-004` returned 404 and were replaced.

---

## Business rules

- **Strict grounding**: answer only with facts explicitly present in `base_conocimiento.md`. Never invent prices, dates or requirements.
- **Escalation**: if the question is out-of-scope or evidence is insufficient, reply `"Sorry, out of scope... human advisor"` and, if `HUMAN_AGENT_CHAT_ID` is set, notify the human via Telegram.
- **Tone**: natural, concise, professional Spanish (see `SYSTEM_PROMPT`).
- **Language**: UI and answers in Spanish; documentation is bilingual.

---

## Security

- `.env` is in `.gitignore:7` and **never** committed. `.env.example` is the template.
- Variables are read only via `backend/config.py:4` (`load_dotenv`).
- No secrets in code, logs or `docs/knowledge/`; logs never print tokens.
- To rotate keys, edit `.env` and restart `python main.py`.

---

## Verification & tests

Commands already executed in this deliverable (Python 3.12.3, `pip check` clean):

```bash
# Compile
python -m py_compile backend/*.py main.py  # OK

# Offline RAG (no Gemini)
python -c "from backend.rag_engine import RAGEngine; r=RAGEngine.__new__(RAGEngine); r.doc_dir='docs/knowledge'; r.cache={}; r.vector_store=None; r._load_documents(); print(r._offline_response('cuanto cuesta', r._offline_search('cuanto cuesta')))"
# → Según la base de conocimiento, los precios son: Bots ... $150 USD; Python ... $280 USD; Prompt ... $160 USD.

# Web API
python -c "from backend.web_app import create_app; c=create_app().test_client(); print(c.get('/api/status').json); print(c.post('/api/chat', json={'message':'hola'}).json)"
# → status ok, telegram_enabled true, hola → reply

# Info and hours
curl http://localhost:5002/api/info      # 5 items with Horario
curl http://localhost:5002/api/status    # rag_ready true
curl -X POST http://localhost:5002/api/chat -H "Content-Type: application/json" -d '{"message":"who is the president of france?"}'
# → escalate offline
```

**Validated functional checklist:**
- [x] `GET /` renders `index.html` with info bar.
- [x] `GET /api/info` returns Courses/Price/Support/Admissions/Hours.
- [x] `GET /api/status` reflects real token (not FAISS).
- [x] `POST /api/chat` validates empty → 400.
- [x] Offline answers prices, 7-day refund, Mon-Fri hours, requirements, duration, certificate, hello; out-of-scope escalates.
- [x] Gemini with quota → uses Gemini; without quota/404 → offline fallback <3s (thanks to fast-retry patch + circuit-breaker).
- [x] Busy port → `get_available_port` picks next automatically.
- [x] Without `TELEGRAM_BOT_TOKEN` → web stays alive.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Telegram disabled` | Empty `TELEGRAM_BOT_TOKEN` | Put your @BotFather token in `.env` and restart. Web is unaffected. |
| `429 Quota exceeded` (Gemini) | Free-tier limit (20 req/day for `2.5-flash-lite`, 100 embeds/min) | Normal: code falls back offline immediately and enables 60s circuit-breaker (`backend/rag_engine.py:87`). Wait or switch to paid API. See https://ai.google.dev/gemini-api/docs/rate-limits |
| `404 model not found` | Old model (`1.5-flash`, `text-embedding-004`) | Already fixed to `gemini-3.6-flash` / `gemini-embedding-2`. Update `GEMINI_MODEL` if you use another. |
| `No free port found` | All ports 5000-65535 busy | Free it: `lsof -i :5002` + `kill <PID>` or use `PORT=5010 python main.py`. |
| `No valid documents` | `docs/knowledge/` empty or wrong path | Verify `docs/knowledge/base_conocimiento.md` exists (256 lines). `main.py:35` warns. |
| Blank web / `template not found` | Ran from another folder | Use `python main.py` from project root; `web_app.py:11` now uses absolute path. |
| `faiss` fails on Mac M1 | Missing `libomp` | `brew install libomp` then `pip install faiss-cpu`. |
| Messages not reaching human | Wrong `HUMAN_AGENT_CHAT_ID` | Use `@userinfobot` on Telegram, forward a message to the bot and copy the `Id`. |

---

## Credits & deliverable

- **Language**: Python 3.12
- **AI**: Google Gemini (`ChatGoogleGenerativeAI`, `GoogleGenerativeAIEmbeddings`)
- **Framework**: LangChain (`langchain_community`, `langchain_google_genai`, `langchain_text_splitters`)
- **Vector DB**: FAISS (`faiss-cpu`)
- **Docs**: `PyPDFLoader`, `TextLoader`, `RecursiveCharacterTextSplitter(800/100)`
- **Web**: Flask 3.0.3 + vanilla HTML/CSS/JS
- **Telegram**: `python-telegram-bot` 21.1.1

Delivered as a **complete functional deliverable** with web chat, Telegram support, local RAG, Gemini integration, human escalation, quota handling and bilingual documentation. The app starts in one command and never crashes due to non-critical external errors.

> **Sora** — Academy of Technology & AI Assistant. Available 24/7 on web and Telegram for courses, pricing, enrollment, refunds and support.
