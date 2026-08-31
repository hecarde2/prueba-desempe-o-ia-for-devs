# Bot de Soporte al Cliente con IA (Telegram + Gemini RAG)

Bot de atención al cliente automatizado para Telegram que usa **RAG (Retrieval-Augmented Generation)** para responder consultas sobre cursos, precios, inscripciones y reembolsos de una academia, con la capacidad de escalar preguntas no resueltas a un asesor humano.

## Tecnologías

- **Python** 3.10+
- **Telegram** — interfaz del bot vía `python-telegram-bot`
- **LangChain** — orquestación del flujo RAG
- **FAISS** — base de datos vectorial para búsqueda de contexto
- **Google Gemini** — embeddings (`text-embedding-004`) y LLM (`gemini-1.5-flash`)
- **PyPDF** — lectura de documentos PDF

## Arquitectura

1. **Interfaz de Telegram**: construida con `python-telegram-bot` en modo *polling*.
2. **Núcleo RAG**: carga documentos desde `documents/`, los divide en fragmentos y crea un índice FAISS con embeddings de Gemini.
3. **LLM**: `gemini-1.5-flash` con temperatura baja (0.1), reglas estrictas de anclaje a la base de conocimientos y ejemplos *few-shot*.
4. **Capa de caché**: un diccionario en memoria guarda respuestas repetidas para optimizar el uso de la API y los tiempos de respuesta.
5. **Escalamiento a humano**: si la pregunta no puede responderse con el contexto disponible, se notifica a un asesor humano por Telegram.

## Estructura del proyecto

```
.
├── main.py                      # Punto de entrada (inicia el bot)
├── requirements.txt             # Dependencias de Python
├── .env.example                 # Plantilla de variables de entorno
├── .gitignore                   # Archivos excluidos de control de versiones
├── documents/                   # Base de conocimiento
│   └── base_conocimiento.md
└── src/
    ├── __init__.py              # Marca `src/` como paquete Python
    ├── config.py                # Carga y valida variables de entorno
    ├── bot.py                   # Lógica del bot de Telegram
    └── rag_engine.py            # Pipeline RAG (documentos, vectores, LLM)
```

## Requisitos previos

- Python 3.10 o superior
- Clave API de Google Gemini (desde [Google AI Studio](https://aistudio.google.com/))
- Token de bot de Telegram (obtenido con [@BotFather](https://t.me/BotFather))

## Instalación

1. **Clona el repositorio e instala las dependencias** (recomendado usar un entorno virtual):

   ```bash
   python -m venv venv
   source venv/bin/activate        # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configura las variables de entorno**:

   ```bash
   cp .env.example .env
   ```

   Edita `.env` y completa tus credenciales:

   | Variable | Descripción |
   | :--- | :--- |
   | `TELEGRAM_BOT_TOKEN` | Token de tu bot (de @BotFather) |
   | `GOOGLE_API_KEY` | Clave API de Google Gemini |
   | `HUMAN_AGENT_CHAT_ID` | ID de chat de Telegram del asesor humano |

3. **Agrega la base de conocimiento**: coloca tus documentos en la carpeta `documents/`. Se admiten archivos **PDF**, **Markdown (`.md`)** y **texto (`.txt`)**.

4. **Ejecuta la aplicación**:

   ```bash
   python main.py
   ```

## Reglas de anclaje y escalamiento

- Temperatura baja del LLM (`0.1`) para minimizar alucinaciones.
- Si la respuesta no está explícita en la base de conocimiento, el bot responde con `ESCALATE_TO_HUMAN`.
- El sistema envía automáticamente la consulta no resuelta al chat del asesor humano definido en `HUMAN_AGENT_CHAT_ID`.

## Notas de seguridad

- **Nunca** subas tu archivo `.env` al repositorio. Contiene credenciales sensibles.
- El `.gitignore` ya excluye `.env`, `venv/` y `__pycache__/`.
- Si alguna vez llegaste a publicar una clave, revócala y genera una nueva inmediatamente.
