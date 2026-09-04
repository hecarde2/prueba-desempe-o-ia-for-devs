# Backend — Sora AI

> **Lógica del servidor** — RAG, Flask y Telegram.

Este directorio contiene **todo lo que es servidor** (Python). Está separado del frontend para que un desarrollador junior pueda enfocarse solo en la lógica sin perderse en HTML/CSS.

## Estructura

```
backend/
├── config.py       # Lee .env (python-dotenv) → TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY, GEMINI_MODEL, etc.
├── rag_engine.py   # Núcleo RAG (540 líneas): FAISS + Gemini + fallback offline + circuit-breaker
├── web_app.py      # Flask: 4 rutas (/, /api/info, /api/status, /api/chat) + static_folder
├── bot.py          # Telegram: /start + handle_message + escalamiento a humano
└── __init__.py
```

## Flujo

```
Telegram / Web → web_app.py / bot.py → rag_engine.py → FAISS/Gemini → offline si falla → respuesta
```

## Archivos clave

- **config.py (15 líneas):** `load_dotenv()` + `_get_optional()` con `strip()`. No hace validación compleja, solo expone constantes.
- **rag_engine.py (618 líneas):** 
  - `RAGEngine(doc_dir=None)` → busca `docs/knowledge` (nuevo) con fallback a `documents` (legacy).
  - `_init_vector_store()` → `RecursiveCharacterTextSplitter(800/100)` → `FAISS.from_documents(GoogleGenerativeAIEmbeddings)` con fallback `gemini-embedding-001` → `gemini-embedding-2`.
  - `query()` → intenta Gemini con `ThreadPoolExecutor(timeout=2.5s)` y `circuit-breaker 60s`; si falla, offline con `STOPWORDS` + `SEARCH_ALIASES` + tabla de precios.
- **web_app.py (90 líneas):** `create_app()` crea `Flask(template_folder=frontend/templates, static_folder=frontend/static)`. Rutas muy explícitas, sin lógica de negocio.
- **bot.py (67 líneas):** `TelegramRAGBot` con `ApplicationBuilder`, `CommandHandler("start")` y `MessageHandler(TEXT)`. Maneja mensajes vacíos y escalamiento a `HUMAN_AGENT_CHAT_ID`.

## Cómo probar solo el backend

```bash
# Sin levantar Flask, solo RAG:
python -c "from backend.rag_engine import RAGEngine; r=RAGEngine(); print(r.query('hola'))"

# Solo Flask (sin Telegram):
python -c "from backend.web_app import create_app; app=create_app(); app.test_client().get('/api/status')"
```

## Dependencias

Ver `requirements.txt` en la raíz: `Flask`, `python-telegram-bot`, `langchain`, `faiss-cpu`, etc. Instala con `pip install -r requirements.txt`.

## Notas para junior

- Si ves `from backend.xxx` y antes era `from src.xxx`, es por la reorganización. Ambos hacen lo mismo, solo cambió la carpeta.
- `doc_dir` ahora es `docs/knowledge` — si mueves `base_conocimiento.md`, actualiza `rag_engine.py:87` y `web_app.py:24`.
- No hardcodees claves: usa `.env` en la raíz.
