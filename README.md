# Asistente IA Sora — Soporte Académico

> **Academia de Tecnología e IA** · Bot de soporte que responde solo con información oficial del negocio. Combina **interfaz web (Flask) + bot de Telegram + motor RAG (FAISS + Gemini)** con un **respaldo local 100% offline** que mantiene la app viva aunque Gemini esté sin cuota, con modelo no disponible o sin credenciales.

Funciona en **dos capas** que el código alterna automáticamente:
1. **Capa inteligente (Gemini)**: si `GOOGLE_API_KEY` es válida y hay cuota, usa embeddings `gemini-embedding-001` + LLM `gemini-2.5-flash-lite` / `gemini-3.6-flash` para respuestas con contexto.
2. **Capa local (offline)**: si la API falla, el motor busca en `documents/base_conocimiento.md` con búsqueda por tokens + aliases y responde sin inventar. Si no hay evidencia, escala a humano.

---

## Índice
1. [Inicio rápido](#inicio-rápido-60-segundos)
2. [Requisitos previos](#requisitos-previos)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Configuración paso a paso](#configuración-paso-a-paso)
5. [Variables de entorno](#variables-de-entorno)
6. [Ejecución](#ejecución)
7. [Cómo usarlo](#cómo-usarlo-ejemplos-reales)
8. [Cómo funciona](#cómo-funciona)
9. [API del backend](#api-del-backend)
10. [Motor RAG en detalle](#motor-rag-en-detalle)
11. [Reglas de negocio](#reglas-de-negocio)
12. [Seguridad](#seguridad)
13. [Verificación y tests](#verificación-y-tests)
14. [Solución de problemas](#solución-de-problemas)
15. [Créditos y entregable](#créditos-y-entregable)

---

## Inicio rápido (60 segundos)

```bash
# 1. Clonar / descomprimir y entrar
cd "prueba-desempe-o-ia-for-devs (entrega)"

# 2. Entorno + dependencias
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configurar credenciales
cp .env.example .env
nano .env                       # completa TELEGRAM_BOT_TOKEN y GOOGLE_API_KEY

# 4. Ejecutar
python main.py
# Abre http://localhost:5002  (si 5002 está ocupado, la app elige otro y lo imprime)
```

> Si no defines `TELEGRAM_BOT_TOKEN` la web funciona igual y el bot simplemente queda deshabilitado.

---

## Requisitos previos

| Requisito | Versión / Detalle | Dónde obtenerlo |
|-----------|-------------------|-----------------|
| Python | **3.10+** (probado en **3.12.3**) | `python3 --version` |
| pip | incluido con Python | `pip --version` |
| Token de Telegram | Bot creado con @BotFather | https://t.me/BotFather |
| Clave Gemini | Google AI Studio | https://aistudio.google.com/app/apikey |
| ID de chat humano | Tu ID de Telegram para escalamientos | Ver paso 4.3 abajo |

**Dependencias principales** (`requirements.txt`):

```
python-telegram-bot==21.1.1
Flask==3.0.3
langchain==0.1.20 · langchain-google-genai==1.0.3 · langchain-community==0.0.38
faiss-cpu==1.8.0 · pypdf==4.2.0 · python-dotenv==1.0.1
```

Todas compatibles con Python 3.12 y verificadas con `pip check`.

---

## Estructura del proyecto

```text
.
├── main.py                     # arranque web + bot (detecta puerto libre)
├── requirements.txt
├── .env.example                # plantilla de variables
├── .env                        # tus claves (no se versiona, ver .gitignore)
├── README.md / README.en.md
├── DOCUMENTACION_PROYECTO.md
├── documents/
│   └── base_conocimiento.md    # ÚNICA fuente de verdad (9 secciones, 25.5k)
├── src/
│   ├── config.py               # carga .env + valida tipos
│   ├── rag_engine.py           # RAG: FAISS + Gemini + fallback offline + circuit-breaker
│   ├── web_app.py              # Flask: /, /api/info, /api/status, /api/chat
│   └── bot.py                  # Telegram: /start + handle_message + escalamiento
└── templates/
    └── index.html              # chat web + barra de info (fetch a /api/*)
```

`documents/base_conocimiento.md` contiene **toda** la información oficial (oferta académica, precios, inscripción, políticas, soporte, labs, mentorías, I+D).

---

## Configuración paso a paso

### 1. Crear y activar entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows PowerShell/CMD
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Copiar variables de entorno

```bash
cp .env.example .env
```

### 3. Obtener cada credencial

#### 3.1 Telegram — `TELEGRAM_BOT_TOKEN`
1. Abre Telegram → busca `@BotFather` → `/newbot`.
2. Sigue el asistente, elige nombre y username → copia el token `123456:AAH...`.
3. Pégalo en `.env` como `TELEGRAM_BOT_TOKEN=123456:AAH...`.
4. *Opcional:* si no lo configuras, la app inicia solo la web (ver `src/bot.py:44`).

#### 3.2 Google Gemini — `GOOGLE_API_KEY` + modelos
1. Ve a https://aistudio.google.com/app/apikey → **Create API key**.
2. Copia la clave (`AIza...` o `AQ.Ab8...` según proyecto) → `GOOGLE_API_KEY=...` en `.env`.
3. Modelos por defecto (ya configurados, no necesitas cambiarlos salvo que quieras):
   ```env
   GEMINI_MODEL=gemini-2.5-flash-lite
   GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
   ```
   El código hace fallback automático a `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-3.5-flash` si el principal falla o está sin cuota (`src/rag_engine.py:70`).

#### 3.3 Humano para escalamientos — `HUMAN_AGENT_CHAT_ID`
1. En Telegram busca `@userinfobot` → `/start` → copia tu ID numérico.
2. En `.env` pon `HUMAN_AGENT_CHAT_ID=123456789`.
3. Cuando alguien pregunta fuera de scope, el bot envía `⚠️ Escalamiento Requerido` a ese chat (`src/bot.py:33`).

### 4. `.env` final de ejemplo

```env
TELEGRAM_BOT_TOKEN=1234567890:AAH...tu_token...
GOOGLE_API_KEY=AIza...tu_clave...
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=1301721795
PORT=5002
```

> `HUMAN_AGENT_CHAT_ID=0` desactiva notificaciones humanas. `PORT` es opcional.

---

## Variables de entorno

| Variable | Obligatoria | Valor por defecto | Descripción |
|----------|-------------|-------------------|-------------|
| `TELEGRAM_BOT_TOKEN` | No | `""` | Token de @BotFather. Si está vacío, el bot no arranca pero la web sí (`main.py:40`). |
| `GOOGLE_API_KEY` | No | `""` | Clave Gemini. Si falta, FAISS no se inicializa y todo va por offline (`src/rag_engine.py:85`). |
| `GEMINI_MODEL` | No | `gemini-2.5-flash-lite` | Modelo de chat. Lista de fallback en `GEMINI_CHAT_MODELS`. |
| `GEMINI_EMBEDDING_MODEL` | No | `models/gemini-embedding-001` | Modelo de embeddings. Fallback `models/gemini-embedding-2`. |
| `HUMAN_AGENT_CHAT_ID` | No | `0` | ID numérico del asesor. Usa `@userinfobot`. |
| `PORT` | No | `5002` | Puerto preferido. `get_available_port()` (`main.py:11`) busca uno libre hasta 65535. |

Nunca hardcodees claves: se cargan con `python-dotenv` en `src/config.py:4`.

---

## Ejecución

### Opción A — Web + Telegram juntos (recomendado)

```bash
python main.py
```

Salida esperada:
```
Base de conocimiento cargada: 1 documento(s).
Vector store (FAISS + Gemini embeddings) inicializado correctamente.
Bot de Telegram arrancado en segundo plano.
Interfaz web disponible en http://localhost:5002
 * Running on http://0.0.0.0:5002
```

Abre `http://localhost:5002` y habla con Sora. Si configuraste el bot, abre Telegram y escribe `/start`.

### Opción B — Solo web (sin Telegram)

```bash
# Deja TELEGRAM_BOT_TOKEN vacío en .env
python main.py
# → "Telegram deshabilitado: no hay TELEGRAM_BOT_TOKEN definido."
```

### Opción C — Puerto personalizado

```bash
PORT=5000 python main.py
# o
PORT=5010 python main.py
```

Si el puerto está ocupado, `main.py:11` prueba el siguiente hasta encontrar uno libre y lo imprime.

### Detener

`Ctrl+C` en la terminal. El proceso del bot es `daemon=True` y termina con la web.

---

## Cómo usarlo (ejemplos reales)

Prueba estas preguntas en la web o en Telegram:

| Pregunta | Respuesta esperada | Origen |
|----------|-------------------|--------|
| `¿Cuánto cuesta el curso de bots?` | `Bots con Telegram e IA: $150 USD | pronto pago $120 USD (hasta el 20) | 2 cuotas 2 x $75 USD` | Offline / Gemini |
| `¿Cuál es el precio del curso de python?` | `$280 USD` + planes | Offline / Gemini |
| `¿Cuánto cuesta?` (sin curso) | Lista de los 3 precios regulares | Offline |
| `¿Cómo pedir reembolso?` | `7 días naturales → 100% sin preguntas` | Offline |
| `¿Cuál es el horario de atención?` | `Lunes a Viernes 8:00-18:00 GMT-5. Sábados 9:00-13:00` | Offline |
| `¿Requisitos del curso de bots?` | `Conocimientos básicos de Python...` | Offline |
| `¿Duración del curso?` | `4 semanas (20 horas lectivas ...)` | Offline |
| `Hola` | Saludo de Sora (no escala) | Offline |
| `¿Quién es el presidente de Francia?` | `Lo siento, fuera del alcance... asesor humano` + escalamiento Telegram | Offline `escalate` |

Todas las respuestas offline fueron validadas con `src/rag_engine.py:_offline_response`.

---

## Cómo funciona

```
Usuario (Web/Telegram)
        ↓
  ┌─────────────┐
  │  RAGEngine  │  src/rag_engine.py:84
  │  1. Carga documents/*.md|pdf → TextLoader/PyPDFLoader
  │  2. Splitter 800/100 → RecursiveCharacterTextSplitter
  │  3. FAISS.from_documents(GoogleGenerativeAIEmbeddings)
  └─────────────┘
        ↓  similarity_search(k=3)
  ┌─────────────┐
  │   Gemini    │  ChatGoogleGenerativeAI(temperature=0.1)
  │  2-4 intentos │ GEMINI_CHAT_MODELS con parche de retry rápido (1 intento)
  │  + SYSTEM_PROMPT con ESCALATE_TO_HUMAN
  └─────────────┘
        ↓ si 429/quota/404/500 → circuit-breaker 60s
  ┌─────────────┐
  │ Offline     │  _offline_search (STOPWORDS + aliases) → _offline_response
  │  - tabla de precios parseada
  │  - horarios vía regex Lunes a Viernes
  │  - reembolso/inscripción/duración/certificado
  │  - best_matching_lines umbral 5
  └─────────────┘
        ↓
   Respuesta {action: reply|escalate, mode: gemini|offline}
        ↓
  Web (/api/chat) o Telegram (reply + notificación humana)
```

**Flujo de la web (`src/web_app.py`):**
- `GET /` → `render_template("index.html")`
- `GET /api/info` → parsea `base_conocimiento.md` con regex y devuelve 5 pills (Cursos, Precio, Soporte, Admisiones, Horario)
- `GET /api/status` → `{status:ok, telegram_enabled: bool(TELEGRAM_BOT_TOKEN), rag_ready, vector_store_ready}`
- `POST /api/chat {message}` → `rag.query()` → `{answer, action, mode}`

**Flujo de Telegram (`src/bot.py`):**
- `CommandHandler("start")` → saludo
- `MessageHandler(TEXT)` → `rag.query()` → `reply_text` → si `escalate` y `HUMAN_AGENT_CHAT_ID` → `send_message` al humano.

---

## API del backend

### `GET /`

HTML del chat. `templates/index.html` hace `fetch('/api/info')` y `fetch('/api/chat')`.

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
  -d '{"message":"¿Cuánto cuesta el curso de bots?"}'
```

```json
{
  "answer":"Según la base de conocimiento: Bots con Telegram e IA: $150 USD | pronto pago $120 USD (hasta el 20) | 2 cuotas 2 x $75 USD.",
  "action":"reply",
  "mode":"offline"
}
# action = "escalate" cuando está fuera de scope
# mode = "gemini" cuando respondió Gemini, "offline" cuando usó respaldo local
```

Error validación:

```bash
curl -X POST http://localhost:5002/api/chat -H "Content-Type: application/json" -d '{"message":""}'
# → 400 {"error":"Escribe una pregunta antes de enviar."}
```

---

## Motor RAG en detalle

**Archivo:** `src/rag_engine.py` (540 líneas) — núcleo del sistema.

| Etapa | Detalle | Código |
|-------|---------|--------|
| **Carga** | Lee `documents/` ordenado; `.pdf` con `PyPDFLoader`, `.md/.txt` con `TextLoader(utf-8)` | `:_load_documents:94` |
| **Split** | `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)` | `:_init_vector_store:114` |
| **Embeddings** | `GoogleGenerativeAIEmbeddings` con fallback `gemini-embedding-001` → `gemini-embedding-2` | `:77` |
| **Vector store** | `FAISS.from_documents(chunks, embeddings)` | `:121` |
| **Búsqueda** | `similarity_search(k=3)` → contexto `"\n---\n".join(docs)` | `:494` |
| **LLM** | `ChatGoogleGenerativeAI(temperature=0.1, max_retries=0)` con `SYSTEM_PROMPT` que obliga a responder `ESCALATE_TO_HUMAN` si no hay evidencia | `:500` |
| **Parche de retry** | `_create_retry_decorator` → `stop_after_attempt(1)` para que cuota no bloquee 60s, fallback inmediato | `:16` |
| **Circuit-breaker** | `_quota_blocked_until = now+60s` tras 429 → siguientes queries evitan Gemini y van directo offline | `:87,526` |
| **Offline search** | Normaliza (NFKD sin tildes), filtra `STOPWORDS` (el, la, de, que...), puntúa por tokens + `SEARCH_ALIASES` por categoría | `:_offline_search:140` |
| **Offline response** | Prioridad: precios (tabla parseada) → requisitos → reembolso (7 días) → inscripción → duración → certificado → horarios → contenido → modalidad → `best_matching_lines` (umbral 5) → escalamiento si 0 overlap | `:_offline_response:254` |
| **Cache** | `dict` por pregunta normalizada | `:489` |

**Modelos vigentes 2026** (verificados con `genai.list_models()`): `gemini-2.5-flash-lite`, `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-3.5-flash`. Los antiguos `gemini-1.5-flash` y `text-embedding-004` daban 404 y fueron reemplazados.

---

## Base de conocimiento

**Único archivo:** `documents/base_conocimiento.md` — 256 líneas, 9 secciones:

1. **Oferta Académica** — 3 cursos (Bots 4 semanas/20h, Python 8 semanas/40h, Prompt 4 semanas/20h) con temario de 5 módulos cada uno.
2. **Precios** — tabla con regular/pronto pago/cuotas + métodos (Stripe, SPEI, PSE, SEPA, Mercado Pago, cripto, PayPal 5%) + descuentos (exalumnos 15%, grupal 20-30%, becas 50%).
3. **Inscripción y Calendario** — flujo 5 pasos + cohortes primer lunes del mes + requisitos técnicos (Win10/macOS11/Ubuntu20.04, 8GB RAM, 10GB SSD).
4. **Políticas y Garantías** — reembolso **7 días naturales 100%**, congelamiento 6 meses, transferencia sin costo, IP del estudiante.
5. **Ecosistema LMS/Discord** — acceso vitalicio, canal `#dudas-tecnicas` <12h, empleos freelance.
6. **Soporte y Contacto** — `Horarios: Lun-Vie 8:00-18:00 GMT-5, Sáb 9:00-13:00`, `soporte@academiatech.com`, `admisiones@academiatech.com`, `@SoporteAcademiaBot`.
7. **Infraestructura cloud** — Colab Pro + SageMaker, GPUs T4/V100, 100h/mes, Docker + EC2/S3.
8. **Mentorías y Empleo** — 40 empresas aliadas, pasantías 8 semanas Scrum, mentoring 1-a-1 2×45min.
9. **Club I+D** — semilleros, GraphRAG, QLoRA, hackathons trimestrales 48h.

Se carga con `TextLoader` y se indexa en FAISS; también alimenta la barra superior de la web vía `/api/info`.

---

## Reglas de negocio

- **Grounding estricto**: solo responde con hechos que aparecen explícitos en `base_conocimiento.md`. Nunca inventa precios, fechas ni requisitos.
- **Escalamiento**: si la pregunta está fuera de scope o no hay evidencia suficiente, responde `"Lo siento, esa consulta está fuera del alcance..."` y, si `HUMAN_AGENT_CHAT_ID` está configurado, notifica al humano por Telegram.
- **Tono**: español natural, breve, profesional (ver `SYSTEM_PROMPT`).
- **Idioma**: interfaz y respuestas en español; documentación bilingüe.

---

## Seguridad

- `.env` está en `.gitignore:7` y **nunca** se commitea. `.env.example` es la plantilla.
- Variables se leen solo con `src/config.py:4` (`load_dotenv`).
- No hay secretos en código, logs ni en `documents/`; los logs no imprimen tokens.
- Si necesitas rotar claves, edita `.env` y reinicia `python main.py`.

---

## Verificación y tests

Comandos que ya fueron ejecutados en este entregable (Python 3.12.3, `pip check` sin rotos):

```bash
# Compilación
python -m py_compile src/*.py main.py  # OK

# RAG offline (sin Gemini)
python -c "from src.rag_engine import RAGEngine; r=RAGEngine.__new__(RAGEngine); r.doc_dir='documents'; r.cache={}; r.vector_store=None; r._load_documents(); print(r._offline_response('cuanto cuesta', r._offline_search('cuanto cuesta')))"
# → Según la base de conocimiento, los precios son: Bots ... $150 USD; Python ... $280 USD; Prompt ... $160 USD.

# Web API
python -c "from src.web_app import create_app; c=create_app().test_client(); print(c.get('/api/status').json); print(c.post('/api/chat', json={'message':'hola'}).json)"
# → status ok, telegram_enabled true, hola → reply

# Info y horarios
curl http://localhost:5002/api/info      # 5 items con Horario
curl http://localhost:5002/api/status    # rag_ready true
curl -X POST http://localhost:5002/api/chat -H "Content-Type: application/json" -d '{"message":"quien es el presidente de francia"}'
# → escalate offline
```

**Checklist funcional validado:**
- [x] `GET /` renderiza `index.html` con barra de info.
- [x] `GET /api/info` devuelve Cursos/Precio/Soporte/Admisiones/Horario.
- [x] `GET /api/status` refleja token real (no FAISS).
- [x] `POST /api/chat` valida vacío → 400.
- [x] Offline responde precios, reembolso 7 días, horario Lun-Vie, requisitos, duración, certificado, hola; fuera de scope escala.
- [x] Gemini con cuota → usa Gemini; sin cuota/404 → fallback offline <3s (gracias al parche de retry + circuit-breaker).
- [x] Puerto ocupado → `get_available_port` elige otro automáticamente.
- [x] Sin `TELEGRAM_BOT_TOKEN` → web sigue viva.

---

## Solución de problemas

| Problema | Causa | Solución |
|----------|-------|----------|
| `Telegram deshabilitado` | `TELEGRAM_BOT_TOKEN` vacío | Pon tu token de @BotFather en `.env` y reinicia. La web no se ve afectada. |
| `429 Quota exceeded` (Gemini) | Límite free-tier (20 req/día para `2.5-flash-lite`, 100 embeds/min) | Normal: el código hace fallback offline inmediato y activa circuit-breaker 60s (`src/rag_engine.py:87`). Espera o cambia a API de pago. Ver https://ai.google.dev/gemini-api/docs/rate-limits |
| `404 model not found` | Modelo antiguo (`1.5-flash`, `text-embedding-004`) | Ya corregido a `gemini-3.6-flash` / `gemini-embedding-2`. Actualiza `GEMINI_MODEL` si usas otro. |
| `No se encontró puerto libre` | Todos los puertos 5000-65535 ocupados | Libera el puerto: `lsof -i :5002` + `kill <PID>` o usa `PORT=5010 python main.py`. |
| `No valid documents` | `documents/` vacío o ruta mal | Verifica que `documents/base_conocimiento.md` existe y tiene 256 líneas. `main.py:34` lo advierte. |
| Web en blanco / `template not found` | Ejecutaste desde otra carpeta | Usa `python main.py` desde la raíz; `web_app.py:11` ahora usa path absoluto. |
| `faiss` no instala en Mac M1 | Falta `libomp` | `brew install libomp` luego `pip install faiss-cpu`. |
| Mensajes no llegan al humano | `HUMAN_AGENT_CHAT_ID` incorrecto | Usa `@userinfobot` en Telegram, reenvía el mensaje al bot y copia el `Id`. |

---

## Créditos y entregable

- **Lenguaje**: Python 3.12
- **IA**: Google Gemini (`ChatGoogleGenerativeAI`, `GoogleGenerativeAIEmbeddings`)
- **Framework**: LangChain (`langchain_community`, `langchain_google_genai`, `langchain_text_splitters`)
- **Vector DB**: FAISS (`faiss-cpu`)
- **Docs**: `PyPDFLoader`, `TextLoader`, `RecursiveCharacterTextSplitter(800/100)`
- **Web**: Flask 3.0.3 + HTML/CSS/JS vanilla
- **Telegram**: `python-telegram-bot` 21.1.1

Proyecto entregado como **entregable funcional completo** con chat web, soporte Telegram, RAG local, integración Gemini, escalamiento humano, manejo de cuota y documentación bilingüe. La app inicia en un solo comando y nunca se rompe por errores externos no críticos.

> **Sora** — Asistente de la Academia de Tecnología e IA. Disponible 24/7 en web y Telegram para cursos, precios, inscripciones, reembolsos y soporte.

