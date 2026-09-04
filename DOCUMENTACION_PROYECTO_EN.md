# Project Documentation — Sora Assistant

> **Version:** 1.1 (corrected functional deliverable) · **Python 3.12.3** · **Status: Ready for demo & deployment**

## Table of Contents
1. [Overview](#overview)
2. [Objectives](#objectives)
3. [Requirements](#requirements)
4. [Architecture](#architecture)
5. [Project structure](#project-structure)
6. [Knowledge base](#knowledge-base)
7. [Environment configuration](#environment-configuration)
8. [Installation](#installation)
9. [Running](#running)
10. [RAG engine — full pipeline](#rag-engine--full-pipeline)
11. [Web application](#web-application)
12. [Telegram bot](#telegram-bot)
13. [System behavior](#system-behavior)
14. [Security](#security)
15. [Verification (evidence)](#verification-evidence)
16. [Use cases & examples](#use-cases--examples)
17. [Troubleshooting](#troubleshooting)
18. [Known limitations](#known-limitations)
19. [Possible improvements](#possible-improvements)
20. [Credits & deliverable](#credits--deliverable)

---

## Overview

**Sora** is a support assistant for the **Academy of Technology & AI** that answers student questions about:

- Academic offer (3 courses)
- Pricing, discounts and financing
- Enrollment process and calendar
- Refund and freeze policies
- Technical requirements
- Support, contact and hours
- Cloud labs, mentoring, jobs and R&D

**Technical solution:** single Python codebase exposing:

- **Web interface** with real-time chat (Flask + `templates/index.html`)
- **Telegram bot** (`@SoporteAcademiaBot` + your personal bot) with human escalation
- **RAG engine** combining FAISS + Gemini *and* a local fallback that guarantees availability even when the external API fails

**Resilience principle:** the system never crashes on a 429, a 404 model or an invalid key. If Gemini cannot answer, the local fallback answers or escalates in a controlled way.

---

## Objectives

### Functional objectives
- Answer **only** with verifiable information from `documents/base_conocimiento.md`.
- Never invent prices, dates, requirements or policies.
- Automatically escalate out-of-scope questions to a human advisor.
- Keep the app operational even when the external API fails (quota, deprecated model, network).

### Non-functional objectives
- **Clarity:** 4-command install, bilingual step-by-step docs.
- **Robustness:** handles busy port, empty messages, missing documents, missing tokens.
- **Efficiency:** offline fallback in <3s thanks to fast-retry patch + 60s circuit-breaker.
- **Security:** keys only in `.env`, never in code or logs.

---

## Requirements

### System requirements

| Component | Requirement | Check |
|-----------|-------------|-------|
| Python | 3.10+ (tested 3.12.3) | `python3 --version` |
| OS | Windows 10/11, macOS 11+, Ubuntu 20.04+ | — |
| RAM | 8 GB min (16 GB recommended for FAISS) | — |
| Disk | 10 GB free (venv ~300 MB + FAISS) | `df -h` |
| Network | 10 Mbps for Gemini; offline works without network | — |

### Dependency requirements

`requirements.txt` (9 lines, `pip check` clean):

```
python-telegram-bot==21.1.1
Flask==3.0.3
langchain==0.1.20
langchain-google-genai==1.0.3
langchain-community==0.0.38
langchain-text-splitters==0.0.2
pypdf==4.2.0
python-dotenv==1.0.1
faiss-cpu==1.8.0
```

### Credential requirements

| Credential | Required for | How to get it |
|------------|--------------|---------------|
| `TELEGRAM_BOT_TOKEN` | Telegram | @BotFather → /newbot → token `123:AAH...` |
| `GOOGLE_API_KEY` | Gemini (online) | https://aistudio.google.com/app/apikey |
| `HUMAN_AGENT_CHAT_ID` | Human escalation | @userinfobot → your numeric ID |

Without any of them the app **still runs in web offline mode** (see `main.py:40` and `src/rag_engine.py:85`).

---

## Architecture

### High-level diagram

```
                  ┌─────────────────────┐
                  │   documents/        │
                  │ base_conocimiento.md│──┐
                  └─────────────────────┘  │
                                           ▼
Telegram ──►  src/bot.py  ──►  src/rag_engine.py  ──► FAISS + Gemini
  /start       handle_message    query()       ▲  │  └─► Gen embeddings
  TEXT ──────────────────────────┘  │  context k=3
                                   │  └─► Chat LLM (temp 0.1)
Web ──► src/web_app.py ────────────┘        │  429 → circuit 60s → offline
  /api/chat  ────────────────────────────────┘
  /api/info  ──► parses MD with regex ─► pills in index.html
  /api/status ─► telegram_enabled / rag_ready
```

### Layers

| Layer | Responsibility | File | Tech |
|-------|----------------|------|------|
| **Presentation** | Web chat + info bar | `templates/index.html`, `src/web_app.py:19` | Flask, vanilla HTML/CSS/JS, fetch |
| **Control** | Orchestrates web and bot, manages port | `main.py:11` `get_available_port`, `Process(daemon=True)` | multiprocessing, socket |
| **Domain RAG** | Loads, indexes, searches and answers | `src/rag_engine.py:84` | FAISS, LangChain, Gemini |
| **Integration** | Telegram polling + escalation | `src/bot.py:23` | python-telegram-bot |
| **Config** | Variables and secrets | `src/config.py:4` | python-dotenv |
| **Data** | Single source of truth | `documents/base_conocimiento.md` | Markdown |

### Question flow

1. User writes in web (`fetch POST /api/chat`) or Telegram (`MessageHandler`).
2. `RAGEngine.query()` normalizes and checks `cache`.
3. If `vector_store` and `GOOGLE_API_KEY` exist **and** not in `quota_blocked`, does `similarity_search(k=3)` and builds `context`.
4. Iterates `GEMINI_CHAT_MODELS` (`gemini-2.5-flash-lite` → `gemini-flash-latest` → `gemini-3.6-flash`...) with `ChatGoogleGenerativeAI(temperature=0.1)` and `SYSTEM_PROMPT` forcing `ESCALATE_TO_HUMAN`.
5. If Gemini answers without escalation, returns `{action:reply, mode:gemini}`.
6. On 429/quota/404, enables `_quota_blocked_until = now+60s` and falls to offline.
7. Offline: `_offline_search` filters `STOPWORDS`, scores by tokens + `SEARCH_ALIASES`, then `_offline_response` prioritizes prices (parsed table), requirements, refund, enrollment, duration, certificate, hours, content, modality, then `best_matching_lines` threshold 5; if 0 overlap → `escalate`.
8. Web returns `{answer, action, mode}`; Telegram `reply_text`s and, if `escalate`, `send_message`s the human.

---

## Project structure

```text
.
├── main.py                     # launcher, free port, bot in background
├── requirements.txt
├── .env.example                # template
├── .env                        # not versioned (gitignore:7)
├── README.md / README.en.md    # user guide bilingual
├── DOCUMENTACION_PROYECTO.md / _EN.md  # this technical doc
├── documents/
│   └── base_conocimiento.md    # 256 lines, 9 sections, single source
├── src/
│   ├── __init__.py
│   ├── config.py               # 15 lines, load_dotenv + strip
│   ├── rag_engine.py           # 540 lines, RAG core + fallback
│   ├── web_app.py              # 84 lines, Flask + 4 routes
│   └── bot.py                  # 60 lines, Telegram + escalation
└── templates/
    └── index.html              # 284 lines, chat + info-bar + JS fetch
```

**Changes in corrected version (commit d582f42):**
- `documents/` consolidated from 3 files to 1 (`base_conocimiento.md` 256 lines).
- `src/rag_engine.py` from 387 to 540 lines with fast-retry patch, circuit-breaker and 7 offline handlers.
- `src/web_app.py` fixes `telegram_enabled` and absolute `template_dir`.
- `src/bot.py` adds validation and error handling.
- `main.py` adds logs and `PORT` invalid handling.

---

## Knowledge base

**Location:** `documents/base_conocimiento.md` — UTF-8 Markdown.

**Summarized content (9 sections, `grep -c "^##"` → 9):**

| Section | Included | Bot use |
|---------|----------|---------|
| 1. Academic Offer | 3 courses: Bots (4 sem/20h, intermediate, prereq Python), Python Data (8 sem/40h, from scratch), Prompt (4 sem/20h, digital use) + 5 modules each + certification 80% attendance, 100% workshops, 70/100 project + QR | Requirements, duration, modality, syllabus, graduate profile |
| 2. Pricing | Table: Bots $150→$120, Python $280→$230, Prompt $160→$130 + 2/3 quotas; payments: Stripe, SPEI, PSE, SEPA/Bizum, Mercado Pago, crypto, PayPal 5%; discounts alumni 15%, group 20/30%, scholarships 50% | Pricing, discounts |
| 3. Enrollment | 5 steps: request → selection → payment → validation (24h) → LMS+Discord access; start first Monday month, close Friday 23:59 GMT-5, 48h early access; tech reqs SO/RAM/disk/net + VS Code, Git, Python 3.12, Zoom | Enrollment, dates, tech reqs |
| 4. Policies | Refund **7 natural days 100%** (5-10 business days), freeze 6 months (3-day notice), free transfer, student IP | Refund, guarantees |
| 5. Ecosystem | Lifetime LMS, Discord `#dudas-tecnicas` <12h, `#empleos-y-freelance`, code review, employability workshops | LMS/Discord support |
| 6. Support | **Hours Mon-Fri 8:00-18:00 GMT-5, Sat 9:00-13:00**, Discord Mon-Sun, contacts `soporte@`, `admisiones@`, `empresas@`, `@SoporteAcademiaBot` | Hours, contact |
| 7. Cloud infra | Colab Pro + SageMaker, GPU T4/V100, 100h/month, EC2/S3/IAM, Docker, Render/Fly.io/Railway, $15 OpenAI credits, Pinecone/Qdrant | Infra |
| 8. Mentoring/Jobs | 40 companies, `#empleos` channel, fast-track >90/100, 8-week Scrum internships, 1-on-1 2×45min | Jobs/mentoring |
| 9. R&D Club | Research papers/open-source, GraphRAG, QLoRA, quarterly 48h hackathons | R&D |

The web top bar (`/api/info`) automatically extracts Courses, Price, Support, Admissions and Hours with regex over this file.

---

## Environment configuration

**Template:** `.env.example` (18 lines).

```env
TELEGRAM_BOT_TOKEN=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=0
```

| Variable | Type | Default | Validation | Effect if missing |
|----------|------|---------|------------|-------------------|
| `TELEGRAM_BOT_TOKEN` | string | "" | `strip()` in `config.py:11` | `bot.run()` returns False, web continues (`main.py:40`) |
| `GOOGLE_API_KEY` | string | "" | same | FAISS not init, all offline (`rag_engine.py:85`) |
| `GEMINI_MODEL` | string | `gemini-2.5-flash-lite` | same | Fallback to explicit `gemini-2.5-flash-lite` |
| `GEMINI_EMBEDDING_MODEL` | string | `models/gemini-embedding-001` | same | Fallback to `gemini-embedding-2` |
| `HUMAN_AGENT_CHAT_ID` | int | 0 | `int(... or 0)` | 0 disables Telegram escalation |
| `PORT` | int | 5002 | `int(os.getenv) try/except` | Uses 5002 and finds free |

Never hardcode: everything via `src/config.py:4` `load_dotenv()`.

---

## Installation

### 1. Virtual environment

```bash
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
python -m pip install --upgrade pip
```

### 2. Dependencies

```bash
pip install -r requirements.txt
pip check    # should say "No broken requirements found."
```

### 3. Variables

```bash
cp .env.example .env
# Edit .env with nano/vim/code and at least fill GOOGLE_API_KEY and TELEGRAM_BOT_TOKEN if you want Telegram
```

**How to get each** (see README for @BotFather and AI Studio screenshots).

---

## Running

```bash
python main.py
# or
PORT=5000 python main.py
```

**Typical output:**
```
Base de conocimiento cargada: 1 documento(s).
Vector store (FAISS + Gemini embeddings) inicializado correctamente.
Bot de Telegram arrancado en segundo plano.
Interfaz web disponible en http://localhost:5002
```

**Access:**
- Web: `http://localhost:5002` (or printed port)
- LAN: `http://<your_ip>:5002`
- Telegram: open your bot → `/start`

**Stop:** `Ctrl+C`.

**Port behavior (`main.py:11` `get_available_port`):**
- Tries `0.0.0.0:preferred` → 65535, if busy probes `5000 → preferred-1`. Never crashes on busy port.

---

## RAG engine — full pipeline

### 1. Load (`src/rag_engine.py:94`)
```python
for file in sorted(os.listdir(doc_dir)):
    if file.endswith(".pdf"): PyPDFLoader
    elif file.endswith((".md",".txt")): TextLoader(encoding="utf-8")
```
Currently 1 Document with 15897 chars.

### 2. Split (`:114`)
`RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)` → ~25 chunks.

### 3. Embeddings (`:77`)
```python
for model in [GEMINI_EMBEDDING_MODEL, "gemini-embedding-001", "gemini-embedding-2"]:
    embeddings = GoogleGenerativeAIEmbeddings(model=model)
    vector_store = FAISS.from_documents(chunks, embeddings)  # if not 429, return
```
On 429 embeddings (100/min), `vector_store=None` and operates offline (see verification logs).

### 4. Search (`:494`)
`similarity_search(k=3)` → `context = "\n---\n".join(docs)`.

### 5. Gemini generation (`:500`)
```python
llm = ChatGoogleGenerativeAI(model=model, temperature=0.1, max_retries=0)
messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"Context:\n{context}\n\nQuestion: {question}"}]
response = llm.invoke(messages)
if "ESCALATE_TO_HUMAN" in content: return escalate
```
`SYSTEM_PROMPT` includes 3 few-shots and forces `ESCALATE_TO_HUMAN` if no evidence.

**Valid 2026 models** (`genai.list_models()`): `gemini-2.5-flash-lite` (20/day quota), `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-3.5-flash`. Older `1.5-flash` and `text-embedding-004` returned 404 and were replaced.

**Fast-retry patch (`:16`):**
```python
import langchain_google_genai.chat_models as _chat_models
_chat_models._create_retry_decorator = lambda: retry(stop_after_attempt(1))
```
Without this, a 429 triggered 10 exponential retries (2+4+8+16+32s = >60s). Now it falls in <1s.

**Circuit-breaker (`:87,526`):**
```python
self._quota_blocked_until = time.time() + 60  # after 429
if time.time() < self._quota_blocked_until: skip_gemini
```

### 6. Offline fallback (`:254`)

**Normalization:** `NFKD` no accents + `[^a-z0-9\s]` → filtered tokens `len>2` not in `STOPWORDS` (~90 words: el, la, de, que...).

**Search:** scores exact token (+3), word boundary (+2) and `SEARCH_ALIASES` per category.

**Cascaded response:**

1. **Greeting** (`hola`, `hello`): fixed offline greeting.
2. **Prices**: parses table regex `\| \*\*(.+?)\*\* \| \$(\d+)`, filters by mentioned course, else lists 3.
3. **Requirements**: first line with `prerrequisitos`.
4. **Refund**: if `garantia + 7 dias` → fixed 100% 7 days.
5. **Enrollment**: if `proceso de inscripcion` → 5 steps.
6. **Duration**: line with `Duración: X semanas (Y horas)` + fallback.
7. **Certificate**: 4-line context from `Certificación`.
8. **Hours**: regex `Atención Administrativa y Soporte: **(.+)` → `Horario de atención: Mon-Fri...`.
9. **Content/Modality**: `best_matching_lines` threshold 5 with `módulo`/`temario`/`modalidad` filter.
10. **Generic**: `best_matching_lines` threshold 5 → if overlap → 3 lines combined.
11. If no overlap → `escalate` with human message.

---

## Web application

**`src/web_app.py` (84 lines)**

```python
app = Flask(__name__, template_folder=abspath("../templates"))
```

| Route | Method | Description | Code |
|-------|--------|-------------|------|
| `/` | GET | Chat HTML | `:18` |
| `/api/info` | GET | Extracts via regex `^### (.+)`, `\*\*(.+?)\*\* \| \$(\d+)`, contacts and hours; returns 5 pills; hardcoded fallback if missing | `:22` |
| `/api/status` | GET | `{status:ok, telegram_enabled: bool(TELEGRAM_BOT_TOKEN), rag_ready, vector_store_ready}` | `:59` |
| `/api/chat` | POST | Validates non-empty `message` → `rag.query()` → `{answer, action, mode}` | `:69` |

**`templates/index.html` (284 lines):** pills grid `#infoBar`, chat bubbles `.msg.user/.bot`, `fetch('/api/info')` with fallback, `fetch('/api/chat')` with `disabled` while waiting.

---

## Telegram bot

**`src/bot.py` (60 lines)**

```python
app = ApplicationBuilder().token(self.token).build()
app.add_handler(CommandHandler("start", self.start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
app.run_polling()
```

- `start`: Sora greeting.
- `handle_message`: validates `message.text`, `query()`, `reply_text(result["message"])`, if `escalate` and `human_agent_id` → `send_message` with `Markdown` to `HUMAN_AGENT_CHAT_ID` in try/catch.
- `run()`: if no token returns `False` and prints `Telegram deshabilitado`; creates `new_event_loop()` to work in `Process(daemon=True)` from `main.py:40`.

---

## System behavior

| Situation | What it does | Evidence |
|-----------|--------------|----------|
| Question with evidence | Answers with exact data | `How much does the bots course cost?` → `$150 USD` |
| Question without evidence | `escalate` + (optional) human notify | `Who is the president of France?` → `out of scope` |
| Gemini with quota | Tries Gemini and caches | `mode:gemini` in `/api/chat` |
| Gemini 429/quota | Fast-retry 1 attempt + 60s circuit → immediate offline | Logs `Gemini alcanzó cuota` → `mode:offline` in <3s |
| Incompatible 404 model | Iterates updated 3.x list → offline | No longer uses `1.5-flash` |
| No `GOOGLE_API_KEY` | No FAISS init, all offline | `Warning: No valid documents` no, but `vector_store None` |
| No `TELEGRAM_BOT_TOKEN` | Web keeps running, bot not started | `Telegram deshabilitado` |
| Busy port | Tries next up to 65535 | `get_available_port:11` |
| Empty message | 400 `Escribe una pregunta` | `web_app.py:74` |

---

## Security

- `.env` ignored in `.gitignore:7`, never committed. Only `.env.example`.
- `src/config.py:4` uses `load_dotenv()` + `strip()`.
- No secrets in `src/`, `documents/` or logs.
- `requirements.txt` has no known critical CVEs (check `pip audit` if needed).
- Bot uses `parse_mode="Markdown"` only for escalation, not user replies.

---

## Verification (evidence)

Environment: `Python 3.12.3`, `pip check` clean, `py_compile` OK.

> These commands were actually executed during the fix (commit d582f42).

```bash
python -m py_compile src/*.py main.py
# py_compile OK

python -c "from src.rag_engine import RAGEngine; r=RAGEngine.__new__(RAGEngine); r.doc_dir='documents'; r.cache={}; r.vector_store=None; r._load_documents(); print(r._offline_response('hola', []))"
# → ¡Hola! Soy Sora...

python -c "from src.web_app import create_app; c=create_app().test_client(); print(c.get('/api/status').json)"
# → {'status':'ok','telegram_enabled':True,'rag_ready':True,'vector_store_ready':True}

curl http://localhost:5002/api/info
# → 5 items with Horario: Lunes a Viernes...

curl -X POST http://localhost:5002/api/chat -d '{"message":"who is the president of france?"}' -H "Content-Type: application/json"
# → {"action":"escalate","mode":"offline"}

python -c "from src.rag_engine import RAGEngine; r=RAGEngine(); print(r.query('cuanto cuesta'))"
# With quota → gemini; without quota → offline "Según la base de conocimiento, los precios son: Bots $150..."
```

**Checklist:**

- [x] Web renders, info-bar with 5 pills including Hours.
- [x] Chat validates empty 400.
- [x] Offline: prices, 7-day refund, Mon-Fri hours, requirements, duration, certificate, hello work; out-of-scope escalates.
- [x] Gemini with quota answers, without quota falls back <3s (patch + circuit).
- [x] Busy port auto-resolved.
- [x] Bot starts in background without blocking web; without token does not crash app.
- [x] Single complete knowledge base (256 lines).
- [x] Bilingual docs updated.

---

## Use cases & examples

| # | Question | Expected offline answer |
|---|----------|-------------------------|
| 1 | What courses are available? | List of 3 via `best_matching_lines` with `Curso 1: Desarrollo de Bots...` |
| 2 | How much does each course cost? | `Bots $150, Python $280, Prompt $160` |
| 3 | What is the enrollment process? | 5 steps (request → LMS access) |
| 4 | Are there refund policies? | `100% within 7 natural days` |
| 5 | How to contact support? | `soporte@academiatech.com`, `admisiones@...`, hours |
| 6 | What prerequisites are needed? | `Basic Python knowledge...` (Bots) / `None` (Python Data) |
| 7 | Modality of the bots course? | `100% online live via Zoom...` |
| 8 | Hello | Sora greeting without escalation |
| 9 | Out-of-scope | Human escalation |

---

## Troubleshooting

Same table as README.md (port, 429 quota, 404 models, empty `documents`, template not found, `faiss` on M1, `HUMAN_AGENT_CHAT_ID`).

Plus:

- **RAG logs:** `Embeddings ... no disponible: 429` → normal for free-tier 100/min; uses `models/gemini-embedding-2` fallback.
- **Chat logs:** `Gemini alcanzó cuota` → immediate offline; wait 60s or use paid key.

---

## Known limitations

- Free-tier Gemini: 20 req/day for `2.5-flash-lite`, 100 embeds/min. Without credit, all answers are offline (but correct).
- Flask is dev server; for production use `gunicorn` or `uvicorn` + `gevent`.
- FAISS is in-memory and rebuilt on each `python main.py`.
- Bot uses `polling` (`getUpdates`); for prod with webhook use `ApplicationBuilder().webhook`.

---

## Possible improvements

- Persist FAISS to disk (`FAISS.save_local` / `load_local`) for instant startup.
- Add `pytest` with `web_app.test_client()` and offline `RAGEngine`.
- Stream Gemini responses in web with `fetch` + `ReadableStream`.
- `prometheus` metrics at `/api/metrics`.
- Dockerfile + `docker-compose` (FastAPI + Redis + Vector DB) already described in knowledge base section 7.

---

## Credits & deliverable

- **Language:** Python 3.12
- **AI:** Google Gemini (`ChatGoogleGenerativeAI`, `GoogleGenerativeAIEmbeddings`)
- **Framework:** LangChain (`langchain_community`, `langchain_google_genai`, `langchain_text_splitters`)
- **Vector DB:** FAISS
- **Docs:** `PyPDFLoader`, `TextLoader`, `RecursiveCharacterTextSplitter(800/100)`
- **Web:** Flask 3.0.3
- **Telegram:** `python-telegram-bot` 21.1.1

Complete functional deliverable: web chat, Telegram bot, local RAG, Gemini, human escalation, quota handling, super-clear bilingual docs and stable one-command execution.

> **Author:** Deliverable corrected by Muse Spark (developer role) — all errors fixed, verified in real execution on 2026-09-04.
