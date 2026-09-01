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

## Instalación y configuración

### 1. Crea un entorno virtual:

```bash
python3 -m venv venv
```

### 2. Activa el entorno virtual:

**En Linux/Mac:**
```bash
source venv/bin/activate
```

**En Windows:**
```bash
venv\Scripts\activate
```

### 3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

### 4. Configura las variables de entorno:

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Edita `.env` y completa las variables:

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
GOOGLE_API_KEY=tu_clave_api_aqui
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=tu_id_chat
```

**Notas importantes:**
- No hardcodees ninguna API key en el código, siempre usa variables de entorno.
- `HUMAN_AGENT_CHAT_ID` debe ser tu ID de usuario en Telegram (donde se escalarán las consultas fuera de scope).
- Si no defines `TELEGRAM_BOT_TOKEN`, la app inicia solo la interfaz web.

## Ejecución

**Asegúrate de estar en el directorio del proyecto y con el entorno virtual activado.**

Desde la raíz:

```bash
python main.py
```

Para elegir un puerto específico:

```bash
PORT=5000 python main.py
```

La app detecta automáticamente un puerto libre si el preferido está ocupado.

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

## Acceso a la aplicación

Tras ejecutar `python main.py`, la interfaz queda disponible en:

```text
http://localhost:5002
```

(Si el puerto 5002 está ocupado, la app automáticamente elige otro puerto libre y lo muestra en la consola)

También puedes acceder desde tu máquina usando la IP de red:

```text
http://<tu_ip>:5002
```

**Para Telegram:** El bot estará activo automáticamente si configuraste `TELEGRAM_BOT_TOKEN`.
