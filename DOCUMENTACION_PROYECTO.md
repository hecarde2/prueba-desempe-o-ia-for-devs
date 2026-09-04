# Documentación del Proyecto

## Descripción general

Este proyecto desarrolla un asistente de soporte para una academia usando inteligencia artificial y recuperación de información basada en documentos. La solución combina:

- una interfaz web con Flask
- un bot de Telegram
- un motor RAG (Retrieval-Augmented Generation)
- integración con Gemini cuando la cuenta tiene cuota disponible
- un respaldo local con la base de conocimiento del negocio para evitar fallos críticos

La finalidad es responder preguntas sobre cursos, precios, requisitos, inscripciones, políticas de reembolso y soporte, siempre apoyándose en la documentación interna del negocio.

## Objetivo

- Responder consultas del cliente con información real y verificable.
- Evitar respuestas inventadas o fuera de contexto.
- Escalar consultas fuera de alcance a un asesor humano.
- Mantener la aplicación funcional aunque falle la API externa.

## Arquitectura

### 1. Interfaz web
La aplicación web está construida con Flask y muestra un chat para interactuar con el asistente. Además, incluye una barra de información estática cargada desde el archivo local de conocimiento.

### 2. Bot de Telegram
El bot usa python-telegram-bot para escuchar mensajes y responder por Telegram. También puede escalar consultas a un chat humano si corresponde.

### 3. Motor RAG
El módulo principal es `src/rag_engine.py`.

Su flujo es:

1. Cargar documentos desde `documents/`
2. Dividir el contenido en fragmentos
3. Construir un índice vectorial con FAISS
4. Buscar contexto relevante según la pregunta
5. Intentar responder con Gemini cuando está disponible
6. Usar el respaldo local si Gemini falla o no hay cuota disponible

### 4. Base de conocimiento
La fuente principal es:

- `documents/base_conocimiento.md`

Este archivo contiene la información de negocio usada para responder consultas y para alimentar la barra de información local en la interfaz visual.

## Estructura del proyecto

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── .env
├── README.md
├── README.en.md
├── DOCUMENTACION_PROYECTO.md
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

## Configuración de entorno

Se usan variables de entorno para evitar hardcodear claves en el código.

Archivo base:

- `.env.example`

Variables:

```env
TELEGRAM_BOT_TOKEN=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
HUMAN_AGENT_CHAT_ID=0
```

### Descripción de cada variable

- `TELEGRAM_BOT_TOKEN`: token del bot de Telegram generado con BotFather.
- `GOOGLE_API_KEY`: clave de Google Gemini.
- `GEMINI_MODEL`: modelo de chat que intenta usar la aplicación.
- `GEMINI_EMBEDDING_MODEL`: modelo de embeddings para la base vectorial.
- `HUMAN_AGENT_CHAT_ID`: ID del chat del asesor humano para escalamiento.

## Instalación

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Crear archivo .env

```bash
cp .env.example .env
```

Luego completar las credenciales reales.

## Ejecución

### Ejecutar la app

```bash
python main.py
```

### Ejecutar con puerto específico

```bash
PORT=5010 python main.py
```

La aplicación detecta un puerto libre si el valor preferido está ocupado.

## Comportamiento del sistema

### Respuesta basada en documentos
La lógica del asistente exige que las respuestas se basen solamente en la información disponible en la base de conocimiento del negocio.

Si la pregunta no está respaldada por la documentación, la app no inventa información y realiza escalamiento.

### Escalamiento a humano
Cuando una consulta está fuera de scope o no existe documentación suficiente, la app devuelve una respuesta de escalamiento y, si se configuró, notifica al agente humano por Telegram.

### Fallback local
Aunque Gemini esté disponible, la app puede fallar por:

- cuota agotada
- modelo no compatible
- error de autenticación
- problema temporal del servicio externo

En esos casos, usa la información local para seguir operando sin romper la aplicación.

## Seguridad

- No se deben hardcodear claves dentro del código.
- El archivo `.env` nunca debe versionarse.
- Los secretos deben manejarse solo desde variables de entorno.

## Verificación realizada

Se comprobó en ejecución real que:

- la app arranca sin fallar por puerto ocupado
- la interfaz web responde correctamente
- la API de información local responde con datos del Markdown
- el bot de Telegram inicia y responde con `getUpdates 200 OK`
- la app mantiene funcionamiento incluso con errores de Gemini o cuota agotada

## Casos de uso principales

- ¿Cuáles son los cursos disponibles?
- ¿Cuánto cuesta cada curso?
- ¿Cuál es el proceso de inscripción?
- ¿Hay políticas de reembolso?
- ¿Cómo contactar al soporte?
- ¿Qué requisitos previos necesito?

## Limitaciones conocidas

- La respuesta generada por Gemini depende de la cuota disponible en la cuenta.
- Si el modelo ya no es compatible o la clave no tiene acceso suficiente, la app usa la base local como respaldo.
- El entorno web se ejecuta en Flask y no está pensado para producción sin un servidor WSGI como gunicorn o equivalente.

## Créditos y entregable

Este proyecto fue desarrollado como entregable funcional con:

- chat web
- soporte por Telegram
- sistema de RAG local
- integración con Gemini
- escalamiento humano
- documentación y ejecución estable


Lenguaje: Python (versión 3.12 según la barra de estado).

Modelos de IA: Google Gemini (ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings).

Framework de IA: LangChain (langchain_community, langchain_google_genai, langchain_text_splitters).

Base de Datos Vectorial / Búsqueda: FAISS (FAISS).

Procesamiento de Documentos: PyPDFLoader y TextLoader para lectura, además de RecursiveCharacterTextSplitter para fragmentar el texto.

Interfaz / Backend: Por las pestañas abiertas (web_app.py, templates/index.html y el puerto local :5002), utiliza un framework web en Python (como Flask o FastAPI) acoplado a HTML/CSS básico para la interfaz gráfica del bot.

Agente IA: Desarrolla un asistente de soporte llamado "Sora" para consultas sobre cursos, horarios, precios e inscripciones.