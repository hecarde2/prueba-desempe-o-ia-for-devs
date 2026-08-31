# Asistente IA para soporte academico

Aplicación que combina una interfaz web, un bot de Telegram y un motor RAG para responder consultas sobre cursos, precios, inscripciones, reembolsos y soporte de una academia.

La app funciona con dos capas:
- una capa inteligente con Gemini cuando la clave y la cuota están disponibles
- una capa local robusta basada en la base de conocimiento del negocio, que responde sin romper la app si Gemini no está disponible, está sobre cuota, o usa un modelo no compatible.

## Objetivo

- Responder consultas solo con la información del negocio.
- Escalar automáticamente cuando la pregunta está fuera de scope o no está en la documentación.
- Mantener la app operativa aunque la API externa falle.
- Soportar interfaz web y Telegram en el mismo proyecto.

## Stack

- Python 3.10+
- Flask para la interfaz web
- python-telegram-bot para Telegram
- LangChain y FAISS para RAG
- Google Gemini para LLM y embeddings
- Markdown y documentos locales en documents/

## Estructura

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── .env
├── README.md
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

## Requisitos previos

- Python 3.10 o superior
- Entorno virtual recomendado
- Token de Telegram del bot generado con @BotFather
- Clave API de Google Gemini desde Google AI Studio

## Configuración

1. Crea un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate
```

2. Instala dependencias:

```bash
pip install -r requirements.txt
```

3. Crea tu archivo de entorno:

```bash
cp .env.example .env
```

4. Completa las variables en .env:

```env
TELEGRAM_BOT_TOKEN=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=0
```

Notas importantes:
- No se debe hardcodear ninguna API key en el código.
- HUMAN_AGENT_CHAT_ID debe ser el ID del chat del agente humano al que se escalarán consultas.
- Si no defines TELEGRAM_BOT_TOKEN, la app inicia solo la web y no el bot.

## Ejecución

Desde la raíz del proyecto:

```bash
source venv/bin/activate
python main.py
```

También puedes elegir un puerto explícito:

```bash
PORT=5010 python main.py
```

La app detecta un puerto libre si el valor preferido está ocupado y evita fallar por conflicto de puertos.

## Cómo funciona

1. Carga la base de conocimiento desde documents/
2. Busca contexto relevante por similitud
3. Intenta responder con Gemini si la API está disponible y hay cuota
4. Si Gemini falla por cuota, modelo no soportado o credenciales inválidas, usa el respaldo local
5. Si la pregunta está fuera del alcance, responde con escalamiento a humano y no inventa información

## Reglas de negocio para la respuesta

- Solo responde con información que aparezca explícitamente en la documentación local.
- Si la respuesta no está en los documentos, debe indicar que requiere revisión humana.
- No genera información no respaldada por la base de conocimiento.
- El sistema responde con tono natural y breve en español.

## Seguridad

- El archivo .env no debe subirse al repositorio.
- Las claves se cargan con variables de entorno.
- No se incluyen secretos en el código ni en los mensajes de logs.

## Verificación realizada

Se validó de forma real que:
- la web responde correctamente
- la API del bot inicia sin romper la app
- la base local responde cuando Gemini no está disponible
- la aplicación arranca sin fallar por puerto ocupado ni por errores no críticos de API externa

## URL de acceso

Tras arrancar, la interfaz queda disponible en:

```text
http://localhost:5010
```

Si el puerto 5010 está ocupado, la app intenta otro puerto libre automáticamente.
