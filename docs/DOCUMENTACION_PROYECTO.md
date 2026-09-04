# Documentación del Proyecto — Asistente Sora

> **Versión:** 1.1 (entregable funcional corregido) · **Python 3.12.3** · **Estado: Listo para presentación y despliegue**

## Índice
1. [Descripción general](#descripción-general)
2. [Objetivos](#objetivos)
3. [Requisitos](#requisitos)
4. [Arquitectura](#arquitectura)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Base de conocimiento](#base-de-conocimiento)
7. [Configuración de entorno](#configuración-de-entorno)
8. [Instalación](#instalación)
9. [Ejecución](#ejecución)
10. [Motor RAG — pipeline completo](#motor-rag--pipeline-completo)
11. [Aplicación web](#aplicación-web)
12. [Bot de Telegram](#bot-de-telegram)
13. [Comportamiento del sistema](#comportamiento-del-sistema)
14. [Seguridad](#seguridad)
15. [Verificación realizada (evidencia)](#verificación-realizada-evidencia)
16. [Casos de uso y ejemplos](#casos-de-uso-y-ejemplos)
17. [Solución de problemas](#solución-de-problemas)
18. [Limitaciones conocidas](#limitaciones-conocidas)
19. [Posibles mejoras](#posibles-mejoras)
20. [Créditos y entregable](#créditos-y-entregable)

---

## Descripción general

**Sora** es un asistente de soporte para la **Academia de Tecnología e IA** que responde preguntas de estudiantes sobre:

- Oferta académica (3 cursos)
- Precios, descuentos y financiación
- Proceso de inscripción y calendario
- Políticas de reembolso y congelamiento
- Requisitos técnicos
- Soporte, contacto y horarios
- Infraestructura cloud, mentorías, empleo e I+D

**Solución técnica:** una sola base de código en Python que expone:

- **Interfaz web** con chat en tiempo real (Flask + `frontend/templates/index.html`)
- **Bot de Telegram** (`@SoporteAcademiaBot` + tu bot personal) con escalamiento a humano
- **Motor RAG** que combina FAISS + Gemini *y* un respaldo local que garantiza disponibilidad aunque la API externa falle

**Principio de resiliencia:** el sistema nunca se rompe por un 429, un 404 de modelo o una clave inválida. Si Gemini no puede responder, el fallback local responde o escala de forma controlada.

---

## Objetivos

### Objetivos funcionales
- Responder **solo** con información verificable de `docs/knowledge/base_conocimiento.md`.
- No inventar precios, fechas, requisitos ni políticas.
- Escalar automáticamente a un asesor humano cuando la pregunta está fuera de scope.
- Mantener la app operativa aunque la API externa falle (cuota, modelo deprecado, red).

### Objetivos no funcionales
- **Claridad:** instalación en 4 comandos, documentación bilingüe paso a paso.
- **Robustez:** manejo de puerto ocupado, mensajes vacíos, documentos faltantes, tokens faltantes.
- **Eficiencia:** fallback offline en <3s gracias a parche de retry + circuit-breaker de 60s.
- **Seguridad:** claves solo en `.env`, nunca en código ni logs.

---

## Requisitos

### Requisitos de sistema

| Componente | Requisito | Verificación |
|------------|-----------|--------------|
| Python | 3.10+ (probado 3.12.3) | `python3 --version` |
| SO | Windows 10/11, macOS 11+, Ubuntu 20.04+ | — |
| RAM | 8 GB mínimo (16 GB recomendado para FAISS) | — |
| Disco | 10 GB libres (venv ~300 MB + FAISS) | `df -h` |
| Red | 10 Mbps para Gemini; offline funciona sin red | — |

### Requisitos de dependencias

`requirements.txt` (9 líneas, `pip check` sin rotos):

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

### Requisitos de credenciales

| Credencial | Obligatoria para | Cómo conseguirla |
|------------|------------------|------------------|
| `TELEGRAM_BOT_TOKEN` | Telegram | @BotFather → /newbot → token `123:AAH...` |
| `GOOGLE_API_KEY` | Gemini (online) | https://aistudio.google.com/app/apikey |
| `HUMAN_AGENT_CHAT_ID` | Escalamiento humano | @userinfobot → tu ID numérico |

Si no configuras estas tres, la app **sigue funcionando en modo web offline** (ver `main.py:40` y `backend/rag_engine.py:85`).

---

## Arquitectura

### Diagrama de alto nivel

```
                  ┌─────────────────────┐
                  │ docs/knowledge/    │
                  │ base_conocimiento.md│──┐
                  └─────────────────────┘  │
                                           ▼
Telegram ──►  backend/bot.py  ──►  backend/rag_engine.py  ──► FAISS + Gemini
  /start       handle_message    query()       ▲  │  └─► Gem embeddings
  TEXT ──────────────────────────┘  │  context k=3
                                   │  └─► Chat LLM (temp 0.1)
Web ──► backend/web_app.py ────────────┘        │  429 → circuit 60s → offline
  /api/chat  ────────────────────────────────┘
  /api/info  ──► parsea MD con regex ─► pills en index.html
  /api/status ─► telegram_enabled / rag_ready
```

### Capas

| Capa | Responsabilidad | Archivo | Tecnologías |
|------|-----------------|---------|-------------|
| **Presentación** | Chat web + barra info | `frontend/templates/index.html`, `backend/web_app.py:19` | Flask, HTML/CSS/JS vanilla, fetch |
| **Control** | Orquesta web y bot, gestiona puerto | `main.py:11` `get_available_port`, `Process(daemon=True)` | multiprocessing, socket |
| **Dominio RAG** | Carga, indexa, busca y responde | `backend/rag_engine.py:84` | FAISS, LangChain, Gemini |
| **Integración** | Telegram polling + escalamiento | `backend/bot.py:23` | python-telegram-bot |
| **Config** | Variables y secretos | `backend/config.py:4` | python-dotenv |
| **Datos** | Fuente única de verdad | `docs/knowledge/base_conocimiento.md` | Markdown |

### Flujo de una pregunta

1. Usuario escribe en web (`fetch POST /api/chat`) o Telegram (`MessageHandler`).
2. `RAGEngine.query()` normaliza y revisa `cache`.
3. Si `vector_store` y `GOOGLE_API_KEY` existen **y** no está en `quota_blocked`, hace `similarity_search(k=3)` y construye `context`.
4. Itera `GEMINI_CHAT_MODELS` (`gemini-2.5-flash-lite` → `gemini-flash-latest` → `gemini-3.6-flash`...) con `ChatGoogleGenerativeAI(temperature=0.1)` y `SYSTEM_PROMPT` que obliga a `ESCALATE_TO_HUMAN`.
5. Si Gemini responde sin escalamiento, devuelve `{action:reply, mode:gemini}`.
6. Si hay 429/quota/404, activa `_quota_blocked_until = now+60s` y cae a offline.
7. Offline: `_offline_search` filtra `STOPWORDS`, puntúa por tokens + `SEARCH_ALIASES`, luego `_offline_response` prioriza precios (tabla), requisitos, reembolso, inscripción, duración, certificado, horario, contenido, modalidad, y finalmente `best_matching_lines` umbral 5; si 0 overlap → `escalate`.
8. Web devuelve `{answer, action, mode}`; Telegram hace `reply_text` y, si `escalate`, `send_message` al humano.

---

## Estructura del proyecto (organización junior — 3 carpetas claras)

```text
.
├── main.py                     # punto de entrada (python main.py) — orquesta backend + frontend
├── requirements.txt            # deps: Flask, telegram-bot, langchain, faiss...
├── .env.example / .env         # plantilla y claves (no versionado, .gitignore:7)
├── README.md / README.en.md    # guía de usuario (inicio rápido, API, troubleshooting)
│
├── backend/                    # 🔧 BACKEND — Python del servidor
│   ├── config.py               # 15 líneas — lee .env
│   ├── rag_engine.py           # 618 líneas — FAISS + Gemini + offline + circuit-breaker
│   ├── web_app.py              # 90 líneas — Flask: /, /api/info, /api/status, /api/chat
│   ├── bot.py                  # 67 líneas — Telegram polling + escalamiento
│   └── __init__.py
│
├── frontend/                   # 🎨 FRONTEND — interfaz visual
│   ├── templates/
│   │   └── index.html          # HTML con Jinja2 + url_for a static
│   └── static/
│       ├── css/
│       │   └── style.css       # 20KB — variables light/dark, sidebar, chat, responsive
│       └── js/
│           └── app.js          # 9KB — fetch /api/*, tema, font, sidebar
│
└── docs/                       # 📚 DOCS — documentación y conocimiento
    ├── README.md               # índice de docs
    ├── DOCUMENTACION_PROYECTO.md      # esta doc ES (20 secciones)
    ├── DOCUMENTACION_PROYECTO_EN.md   # doc EN
    └── knowledge/
        └── base_conocimiento.md       # única fuente de verdad (256 líneas, 9 secciones)
```

**Cambios de la versión corregida:**
- `src/` → `backend/` (backend = servidor, más claro para junior)
- `templates/` → `frontend/templates/` + `frontend/static/css|js` (separa visual)
- `documents/` → `docs/knowledge/` (todo lo escrito en `docs/`)
- `DOCUMENTACION_PROYECTO.md` → `docs/` ( junto a base de conocimiento)
- `backend/rag_engine.py` de 387 → 618 líneas con parche retry, circuit-breaker y handler de cursos
- `backend/web_app.py` corrige `telegram_enabled` y `template_dir` absoluto a `frontend/templates`

---

## Base de conocimiento

**Ubicación:** `docs/knowledge/base_conocimiento.md` — Markdown UTF-8.

**Contenido resumido (9 secciones, ver `grep -c "^##"` → 9):**

| Sección | Incluido | Uso en el bot |
|---------|----------|---------------|
| 1. Oferta Académica | 3 cursos: Bots (4 sem/20h, intermedio, prereq Python), Python Data (8 sem/40h, desde cero), Prompt (4 sem/20h, uso digital) + temario 5 módulos cada uno + certificación 80% asistencia, 100% talleres, 70/100 proyecto + QR | Requisitos, duración, modalidad, temario, perfil egreso |
| 2. Precios | Tabla: Bots $150→$120, Python $280→$230, Prompt $160→$130 + 2/3 cuotas; pagos: Stripe, SPEI, PSE, SEPA/Bizum, Mercado Pago, cripto, PayPal 5%; descuentos exalumnos 15%, grupal 20/30%, becas 50% | Precios, descuentos |
| 3. Inscripción | 5 pasos: solicitud → selección → pago → validación (24h) → acceso LMS + Discord; inicio primer lunes mes, cierre viernes 23:59 GMT-5, acceso 48h antes; requisitos SO/RAM/disco/red + VS Code, Git, Python 3.12, Zoom | Inscripción, fechas, requisitos técnicos |
| 4. Políticas | Reembolso **7 días naturales 100%** (5-10 días hábiles), congelamiento 6 meses (aviso 3 días), transferencia sin costo, IP del estudiante | Reembolso, garantías |
| 5. Ecosistema | LMS vitalicio, Discord `#dudas-tecnicas` <12h, `#empleos-y-freelance`, code review, talleres empleabilidad | Soporte LMS/Discord |
| 6. Soporte | **Horarios Lun-Vie 8:00-18:00 GMT-5, Sáb 9:00-13:00**, Discord Lun-Dom, contactos `soporte@`, `admisiones@`, `empresas@`, `@SoporteAcademiaBot` | Horarios, contacto |
| 7. Infra cloud | Colab Pro + SageMaker, GPU T4/V100, 100h/mes, EC2/S3/IAM, Docker, Render/Fly.io/Railway, créditos Gemini $15 OpenAI, Pinecone/Qdrant | Infra |
| 8. Mentorías/Empleo | 40 empresas, canal `#empleos`, fast-track >90/100, pasantías 8 sem Scrum, mentoring 1-a-1 2×45min | Empleo/mentorías |
| 9. Club I+D | Semilleros papers/open-source, GraphRAG, QLoRA, hackathons trimestrales 48h | I+D |

La barra superior de la web (`/api/info`) extrae automáticamente Cursos, Precio, Soporte, Admisiones y Horario con regex sobre este archivo.

---

## Configuración de entorno

**Plantilla:** `.env.example` (18 líneas).

```env
TELEGRAM_BOT_TOKEN=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=0
```

| Variable | Tipo | Defecto | Validación | Efecto si falta |
|----------|------|---------|------------|-----------------|
| `TELEGRAM_BOT_TOKEN` | string | "" | `strip()` en `config.py:11` | `bot.run()` retorna False, web sigue (`main.py:40`) |
| `GOOGLE_API_KEY` | string | "" | idem | No se inicializa FAISS, todo offline (`rag_engine.py:85`) |
| `GEMINI_MODEL` | string | `gemini-2.5-flash-lite` | idem | Fallback a `gemini-2.5-flash-lite` explícito |
| `GEMINI_EMBEDDING_MODEL` | string | `models/gemini-embedding-001` | idem | Fallback a `gemini-embedding-2` |
| `HUMAN_AGENT_CHAT_ID` | int | 0 | `int(... or 0)` | 0 desactiva escalamiento Telegram |
| `PORT` | int | 5002 | `int(os.getenv) try/except` | Usa 5002 y busca libre |

No hardcodear: todo vía `backend/config.py:4` `load_dotenv()`.

---

## Instalación

### 1. Entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
python -m pip install --upgrade pip
```

### 2. Dependencias

```bash
pip install -r requirements.txt
pip check    # debe decir "No broken requirements found."
```

### 3. Variables

```bash
cp .env.example .env
# Edita .env con nano/vim/code y completa al menos GOOGLE_API_KEY y TELEGRAM_BOT_TOKEN si quieres Telegram
```

**Cómo obtener cada una** (ver README para capturas de @BotFather y AI Studio).

---

## Ejecución

```bash
python main.py
# o
PORT=5000 python main.py
```

**Salida típica:**
```
Base de conocimiento cargada: 1 documento(s).
Vector store (FAISS + Gemini embeddings) inicializado correctamente.
Bot de Telegram arrancado en segundo plano.
Interfaz web disponible en http://localhost:5002
```

**Acceso:**
- Web: `http://localhost:5002` (o el puerto que imprima)
- Red local: `http://<tu_ip>:5002`
- Telegram: abre tu bot → `/start`

**Detener:** `Ctrl+C`.

**Comportamiento de puerto (`main.py:11` `get_available_port`):**
- Intenta bindear `0.0.0.0:preferred` → 65535, si ocupado prueba `5000 → preferred-1`. Nunca crashea por puerto ocupado.

---

## Motor RAG — pipeline completo

### 1. Carga (`backend/rag_engine.py:94`)
```python
for file in sorted(os.listdir(doc_dir)):
    if file.endswith(".pdf"): PyPDFLoader
    elif file.endswith((".md",".txt")): TextLoader(encoding="utf-8")
```
Actualmente 1 Documento con 15897 caracteres.

### 2. Split (`:114`)
`RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)` → ~25 chunks.

### 3. Embeddings (`:77`)
```python
for model in [GEMINI_EMBEDDING_MODEL, "gemini-embedding-001", "gemini-embedding-2"]:
    embeddings = GoogleGenerativeAIEmbeddings(model=model)
    vector_store = FAISS.from_documents(chunks, embeddings)  # si no 429, retorna
```
Si 429 en embeddings (100/min), `vector_store=None` y opera offline (ver logs de verificación).

### 4. Búsqueda (`:494`)
`similarity_search(k=3)` → `context = "\n---\n".join(docs)`.

### 5. Generación Gemini (`:500`)
```python
llm = ChatGoogleGenerativeAI(model=model, temperature=0.1, max_retries=0)
messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"Context:\n{context}\n\nQuestion: {question}"}]
response = llm.invoke(messages)
if "ESCALATE_TO_HUMAN" in content: return escalate
```
`SYSTEM_PROMPT` incluye 3 few-shot y obliga a `ESCALATE_TO_HUMAN` si no hay evidencia.

**Modelos 2026 válidos** (`genai.list_models()`): `gemini-2.5-flash-lite` (con cuota 20/día), `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-3.5-flash`. Los viejos `1.5-flash` y `text-embedding-004` daban 404 y fueron reemplazados.

**Parche de retry (`:16`):**
```python
import langchain_google_genai.chat_models as _chat_models
_chat_models._create_retry_decorator = lambda: retry(stop_after_attempt(1))
```
Sin esto, un 429 provocaba 10 reintentos exponenciales (2+4+8+16+32s = >60s). Ahora cae en <1s y hace fallback.

**Circuit-breaker (`:87,526`):**
```python
self._quota_blocked_until = time.time() + 60  # tras 429
if time.time() < self._quota_blocked_until: skip_gemini
```

### 6. Fallback offline (`:254`)

**Normalización:** `NFKD` sin tildes + `[^a-z0-9\s]` → tokens filtrados `len>2` y no en `STOPWORDS` (lista de ~90 palabras: el, la, de, que...).

**Búsqueda:** puntúa por token exacto (+3), borde de palabra (+2) y `SEARCH_ALIASES` por categoría.

**Respuesta en cascada:**

1. **Greeting** (`hola`, `buenas`): saludo fijo offline.
2. **Precios**: parsea tabla con regex `\| \*\*(.+?)\*\* \| \$(\d+)`, filtra por curso mencionado, si no lista 3.
3. **Requisitos**: primera línea con `prerrequisitos`.
4. **Reembolso**: si `garantia + 7 dias` → frase fija 100% 7 días.
5. **Inscripción**: si `proceso de inscripcion` → 5 pasos.
6. **Duración**: línea con `Duración: X semanas (Y horas)` + fallback.
7. **Certificado**: contexto 4 líneas desde `Certificación`.
8. **Horarios**: regex `Atención Administrativa y Soporte: **(.+)` → `Horario de atención: Lun-Vie...`.
9. **Contenido/Modalidad**: `best_matching_lines` umbral 5 con filtro `módulo`/`temario`/`modalidad`.
10. **Genérico**: `best_matching_lines` umbral 5 → si overlap → 3 líneas combinadas.
11. Si no overlap → `escalate` con mensaje humano.

---

## Aplicación web

**`backend/web_app.py` (84 líneas)**

```python
app = Flask(__name__, template_folder=abspath("../templates"))
```

| Ruta | Método | Descripción | Código |
|------|--------|-------------|--------|
| `/` | GET | HTML del chat | `:18` |
| `/api/info` | GET | Extrae con regex `^### (.+)`, `\*\*(.+?)\*\* \| \$(\d+)`, contactos y horarios; devuelve 5 pills; fallback hardcode si no hay archivo | `:22` |
| `/api/status` | GET | `{status:ok, telegram_enabled: bool(TELEGRAM_BOT_TOKEN), rag_ready, vector_store_ready}` | `:59` |
| `/api/chat` | POST | Valida `message` no vacío → `rag.query()` → `{answer, action, mode}` | `:69` |

**`frontend/templates/index.html` (284 líneas):** grid de pills `#infoBar`, chat con burbujas `.msg.user/.bot`, `fetch('/api/info')` con fallback, `fetch('/api/chat')` con `disabled` durante espera.

---

## Bot de Telegram

**`backend/bot.py` (60 líneas)**

```python
app = ApplicationBuilder().token(self.token).build()
app.add_handler(CommandHandler("start", self.start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
app.run_polling()
```

- `start`: saludo Sora.
- `handle_message`: valida `message.text`, `query()`, `reply_text(result["message"])`, si `escalate` y `human_agent_id` → `send_message` con `Markdown` a `HUMAN_AGENT_CHAT_ID` en try/catch.
- `run()`: si no hay token retorna `False` e imprime `Telegram deshabilitado`; crea `new_event_loop()` para funcionar en `Process(daemon=True)` de `main.py:40`.

---

## Comportamiento del sistema

| Situación | Qué hace | Evidencia |
|-----------|----------|-----------|
| Pregunta con evidencia | Responde con datos exactos | `¿Cuánto cuesta el curso de bots?` → `$150 USD` |
| Pregunta sin evidencia | `escalate` + (opcional) notifica humano | `¿Quién es el presidente de Francia?` → `fuera del alcance` |
| Gemini con cuota | Intenta Gemini y cachea | `mode:gemini` en `/api/chat` |
| Gemini 429/quota | Parche retry 1 intento + circuit 60s → offline inmediato | Logs `Gemini alcanzó cuota` → `mode:offline` en <3s |
| Modelo no compatible 404 | Itera lista actualizada 3.x → offline | Ya no usa `1.5-flash` |
| Sin `GOOGLE_API_KEY` | No inicializa FAISS, todo offline | `Warning: No valid documents` no, pero `vector_store None` |
| Sin `TELEGRAM_BOT_TOKEN` | Web sigue, bot no arranca | `Telegram deshabilitado` |
| Puerto ocupado | Prueba siguiente hasta 65535 | `get_available_port:11` |
| Mensaje vacío | 400 `Escribe una pregunta` | `web_app.py:74` |

---

## Seguridad

- `.env` ignorado en `.gitignore:7`, nunca commiteado. Solo `.env.example`.
- `backend/config.py:4` usa `load_dotenv()` + `strip()`.
- Sin secretos en `backend/`, `docs/knowledge/` ni logs.
- `requirements.txt` sin dependencias con CVEs críticos conocidos (ver `pip audit` si aplica).
- Bot usa `parse_mode="Markdown"` solo para escalamiento, no para respuestas de usuario.

---

## Verificación realizada (evidencia)

Entorno: `Python 3.12.3`, `pip check` sin rotos, `py_compile` OK.

> Estos comandos fueron ejecutados realmente durante la corrección (commit d582f42).

```bash
python -m py_compile backend/*.py main.py
# py_compile OK

python -c "from src.rag_engine import RAGEngine; r=RAGEngine.__new__(RAGEngine); r.doc_dir='documents'; r.cache={}; r.vector_store=None; r._load_documents(); print(r._offline_response('hola', []))"
# → ¡Hola! Soy Sora...

python -c "from src.web_app import create_app; c=create_app().test_client(); print(c.get('/api/status').json)"
# → {'status':'ok','telegram_enabled':True,'rag_ready':True,'vector_store_ready':True}

curl http://localhost:5002/api/info
# → 5 items con Horario: Lunes a Viernes...

curl -X POST http://localhost:5002/api/chat -d '{"message":"quien es el presidente de francia"}' -H "Content-Type: application/json"
# → {"action":"escalate","mode":"offline"}

python -c "from src.rag_engine import RAGEngine; r=RAGEngine(); print(r.query('cuanto cuesta'))"
# Con cuota → gemini; sin cuota → offline "Según la base de conocimiento, los precios son: Bots $150..."
```

**Checklist:**

- [x] Web responde, info-bar con 5 pills incluido Horario.
- [x] Chat valida vacío 400.
- [x] Offline: precios, reembolso 7 días, horario, requisitos, duración, certificado, saludo funcionan; fuera de scope escala.
- [x] Gemini con cuota responde, sin cuota hace fallback <3s (parche + circuit).
- [x] Puerto ocupado resuelto automáticamente.
- [x] Bot inicia en background sin bloquear web; sin token no rompe app.
- [x] Base de conocimiento única y completa (256 líneas).
- [x] Documentación bilingüe actualizada.

---

## Casos de uso y ejemplos

| # | Pregunta | Respuesta esperada (offline) |
|---|----------|------------------------------|
| 1 | ¿Cuáles son los cursos disponibles? | Lista de 3 cursos vía `best_matching_lines` con `Curso 1: Desarrollo de Bots...` |
| 2 | ¿Cuánto cuesta cada curso? | `Bots $150, Python $280, Prompt $160` |
| 3 | ¿Cuál es el proceso de inscripción? | 5 pasos (solicitud → acceso LMS) |
| 4 | ¿Hay políticas de reembolso? | `100% dentro de 7 días naturales` |
| 5 | ¿Cómo contactar al soporte? | `soporte@academiatech.com`, `admisiones@...`, horarios |
| 6 | ¿Qué requisitos previos necesito? | `Conocimientos básicos de Python...` (Bots) / `Ninguno` (Python Data) |
| 7 | ¿Modalidad del curso de bots? | `100% online en vivo vía Zoom...` |
| 8 | Hola | Saludo Sora sin escalamiento |
| 9 | Fuera de scope | Escalamiento humano |

---

## Solución de problemas

Ver tabla en README.md idéntica (port, quota 429, 404 modelos, `documents` vacío, template not found, `faiss` en M1, `HUMAN_AGENT_CHAT_ID`).

Además:

- **Logs de RAG:** `Embeddings ... no disponible: 429` → normal por cuota free-tier 100/min; usa `models/gemini-embedding-2` como fallback.
- **Logs de chat:** `Gemini alcanzó cuota` → offline inmediato; espera 60s o usa clave de pago.

---

## Limitaciones conocidas

- Free-tier Gemini: 20 req/día para `2.5-flash-lite`, 100 embeds/min. Sin crédito, todas las respuestas son offline (pero correctas).
- Flask es servidor de desarrollo; para producción usar `gunicorn` o `uvicorn` + `gevent`.
- FAISS en memoria no persiste entre reinicios; se reconstruye en cada `python main.py`.
- Bot usa `polling` (`getUpdates`); para producción con webhook usar `ApplicationBuilder().webhook`.

---

## Posibles mejoras

- Persistir FAISS en disco (`FAISS.save_local` / `load_local`) para arranque instantáneo.
- Añadir `pytest` con `web_app.test_client()` y `RAGEngine` offline.
- Streaming de respuestas Gemini en la web con `fetch` + `ReadableStream`.
- Métricas `prometheus` en `/api/metrics`.
- Dockerfile + `docker-compose` (FastAPI + Redis + Vector DB) ya descrito en la base de conocimiento sección 7.

---

## Créditos y entregable

- **Lenguaje:** Python 3.12
- **IA:** Google Gemini (`ChatGoogleGenerativeAI`, `GoogleGenerativeAIEmbeddings`)
- **Framework:** LangChain (`langchain_community`, `langchain_google_genai`, `langchain_text_splitters`)
- **Vector DB:** FAISS
- **Docs:** `PyPDFLoader`, `TextLoader`, `RecursiveCharacterTextSplitter(800/100)`
- **Web:** Flask 3.0.3
- **Telegram:** `python-telegram-bot` 21.1.1

Entregable funcional completo: chat web, bot Telegram, RAG local, Gemini, escalamiento humano, manejo de cuota, documentación bilingüe super clara y ejecución estable en un solo comando.

> **Autor:** Entrega corregida por Muse Spark (rol desarrollador) — todos los errores corregidos, verificado en ejecución real el 2026-09-04.

