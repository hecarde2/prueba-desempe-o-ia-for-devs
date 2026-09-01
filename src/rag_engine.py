import os
import re
import unicodedata

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_EMBEDDING_MODEL

try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None
    GoogleGenerativeAIEmbeddings = None

SEARCH_ALIASES = {
    "requisito": ["requisito", "prerrequisito", "preparacion", "preparación", "antes de empezar", "necesita", "necesitas", "se requiere", "se necesita", "requisitos previos", "pre-requisito", "conocimientos previos"],
    "precio": ["precio", "cost", "costo", "cuanto", "cuánto", "pago", "descuento", "tarifa", "valor", "cuesta", "cuestan", "precio del curso", "cuanto cuesta", "cual es el precio", "valores", "inversión", "quanto", "arancel"],
    "reembolso": ["reembolso", "devolucion", "devolución", "cancelacion", "cancelación", "refund", "satisfecho", "quedo satisfecho", "devolucion del 100%", "política de reembolso", "garantía", "dinero de vuelta", "recuperar dinero", "no quedo satisfecho"],
    "inscripcion": ["inscrib", "matricula", "matrícula", "registro", "inicio", "fecha", "clases", "cuotas", "financiamiento", "plazo", "proceso de inscripcion", "como me inscribo", "como inscribirse", "cómo registrarse", "enrolar", "cohort", "cohorte", "admisiones"],
    "horario": ["horario", "atencion", "atención", "soporte", "cuando abren", "cuando esta abierto", "horas de atencion", "horas de atención", "disponibilidad", "abierto", "cierre", "horarios administrativos"],
    "modalidad": ["modalidad", "online", "presencial", "en vivo", "asincrónico", "sincrónico", "zoom", "lms", "plataforma", "formato del curso"],
    "duracion": ["duracion", "duración", "semanas", "horas", "tiempo", "cuanto dura", "cuando termina", "cuándo termina"],
    "profesor": ["profesor", "instructor", "docente", "mentor", "quien enseña", "quién enseña", "facilitador", "tutor", "equipo docente"],
    "contenido": ["contenido", "temario", "módulo", "tema", "qué aprendo", "qué se enseña", "programa", "syllabus", "plan de estudio"],
    "certificado": ["certificado", "diploma", "constancia", "acreditación", "titulación", "credenciales"],
}

SYSTEM_PROMPT = """You are "Sora", the AI support assistant for the Academia de Tecnología e IA.
Your role is to answer student inquiries about courses, schedules, prices, payments, enrollments, refunds, and support strictly using the provided context.

RULES:
1. Grounding: Answer ONLY using the facts present in the context below. If the information is not explicitly mentioned or is out of scope, respond EXACTLY with: "ESCALATE_TO_HUMAN".
2. Tone: Friendly, concise, professional, and written in natural Spanish.
3. Cost Efficiency: Do not write unnecessary prose. Be direct and concise.

FEW-SHOT EXAMPLES:

User: ¿Cuáles son los requisitos para el curso de bots con Telegram?
Context: Prerrequisitos: Conocimientos básicos de Python (variables, funciones y estructuras de control).
Assistant: Para el curso de Desarrollo de Bots con Telegram e IA se requieren conocimientos básicos de Python, como variables, funciones y estructuras de control.

User: ¿Ofrecen descuentos por pronto pago?
Context: Tabla de precios: Bots con Telegram e IA $150 USD. Descuento Pronto Pago (hasta el día 20): $120 USD.
Assistant: Sí, si realizas el pago antes del día 20 del mes obtienes un descuento por pronto pago. El curso de Bots con Telegram e IA pasa de $150 USD a $120 USD.

User: ¿Cómo puedo solicitar un reembolso?
Context: Garantía de reembolso: Puedes solicitar la devolución del 100% de tu dinero dentro de los primeros 7 días naturales tras el inicio del curso.
Assistant: Puedes solicitar la devolución del 100% de tu dinero dentro de los primeros 7 días naturales después del inicio del curso si no quedas satisfecho.
"""

GEMINI_CHAT_MODELS = [
    GEMINI_MODEL,
    "gemini-2.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
]
GEMINI_EMBEDDING_MODELS = [
    GEMINI_EMBEDDING_MODEL,
    "models/gemini-embedding-001",
    "models/text-embedding-004",
]


class RAGEngine:
    def __init__(self, doc_dir: str = "documents"):
        self.doc_dir = doc_dir
        self.vector_store = None
        self.raw_documents = []
        self.cache = {}
        self._load_documents()
        if GOOGLE_API_KEY and GoogleGenerativeAIEmbeddings and ChatGoogleGenerativeAI:
            self._init_vector_store()

    def _load_documents(self):
        documents = []
        if os.path.exists(self.doc_dir):
            for file in sorted(os.listdir(self.doc_dir)):
                file_path = os.path.join(self.doc_dir, file)

                if file.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    documents.extend(loader.load())
                elif file.endswith(".md") or file.endswith(".txt"):
                    loader = TextLoader(file_path, encoding="utf-8")
                    documents.extend(loader.load())

        self.raw_documents = documents

    def _init_vector_store(self):
        if not self.raw_documents:
            print("Warning: No valid documents found in documents directory.")
            return

        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = text_splitter.split_documents(self.raw_documents)

            for model_name in GEMINI_EMBEDDING_MODELS:
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model=model_name)
                    self.vector_store = FAISS.from_documents(chunks, embeddings)
                    return
                except Exception as exc:  # pragma: no cover
                    print(f"Embeddings {model_name} no disponible: {exc}")

            self.vector_store = None
        except Exception as exc:  # pragma: no cover
            print(f"Vector DB no disponible; usando modo offline. Detalle: {exc}")
            self.vector_store = None

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize('NFKD', text.lower())
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9\s]", " ", normalized)

    def _offline_search(self, question: str):
        if not self.raw_documents:
            return []

        normalized_question = self._normalize(question)
        q_tokens = [token for token in normalized_question.split() if token]
        if not q_tokens:
            return []

        scored = []
        for document in self.raw_documents:
            text = self._normalize(document.page_content)
            score = 0
            
            # Puntuación por tokens exactos
            for token in q_tokens:
                if token in text:
                    score += 2
            
            # Puntuación por aliases de categoría
            for category, aliases in SEARCH_ALIASES.items():
                # Si la pregunta contiene un alias de categoría
                matching_aliases_q = [alias for alias in aliases if alias in normalized_question]
                if matching_aliases_q:
                    # Si el documento también contiene esos aliases
                    matching_aliases_doc = [alias for alias in aliases if alias in text]
                    if matching_aliases_doc:
                        score += len(matching_aliases_q) * len(matching_aliases_doc) * 3
            
            # Puntuación por palabras clave relacionadas
            keywords = {
                "curso": 2,
                "modulo": 2,
                "temario": 2,
                "requisito": 2,
                "precio": 2,
                "duracion": 1,
                "modalidad": 1,
                "semanas": 1,
                "horas": 1,
            }
            
            for keyword, weight in keywords.items():
                if keyword in normalized_question and keyword in text:
                    score += weight
            
            # Puntuación por contexto de secciones (si el doc contiene encabezados relevantes)
            if "#" in document.page_content and any(token in normalized_question for token in ["que es", "que aprendo", "contenido"]):
                score += 3
            
            # Puntuación por longitud del documento (docs más largos = más contexto)
            if len(document.page_content) > 500 and score > 0:
                score += 1
            
            if score:
                scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:5]]

    def _best_matching_lines(self, question: str, lines):
        normalized_question = self._normalize(question)
        tokens = {token for token in normalized_question.split() if token}
        scored = []

        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 10:
                continue
            normalized_line = self._normalize(stripped)
            score = 0
            
            # Puntuación por tokens coincidentes
            for token in tokens:
                if token in normalized_line:
                    score += 4
            
            # Puntuación por palabras clave específicas
            key_phrases = {
                "curso": 2,
                "prerequisito": 3,
                "precio": 2,
                "duracion": 2,
                "modalidad": 2,
                "semana": 1,
                "hora": 1,
                "modulo": 2,
                "temario": 2,
                "objetivo": 2,
                "perfil de egreso": 3,
                "contenido": 2,
            }
            
            for phrase, weight in key_phrases.items():
                if phrase in normalized_line:
                    score += weight
            
            # Penalizar líneas muy cortas o muy genéricas
            if len(stripped) < 20:
                score *= 0.5
            
            # Bonificación si contiene números (precios, duraciones)
            if any(char.isdigit() for char in stripped):
                score += 2
            
            if score > 0:
                scored.append((score, stripped))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [line for _, line in scored[:6]]

    def _offline_response(self, question: str, docs):
        if not docs and not self.raw_documents:
            return {
                "action": "escalate",
                "message": "Todavía no tengo información suficiente en esta base de conocimiento para responderte. Puedes intentar otra pregunta o contactar con un asesor humano.",
                "mode": "offline",
            }

        text = "\n".join(doc.page_content for doc in (docs or self.raw_documents))
        q = self._normalize(question)
        lowered = text.lower()
        q_lower = question.lower()

        # Búsqueda de precios
        if any(token in q for token in ["cuanto", "precio", "costo", "descuento", "tarifa", "valor", "cuesta", "arancel", "inversion", "quanto"]):
            prices = re.findall(r"\$\s*\d+(?:\.\d+)?\s*USD", text, flags=re.IGNORECASE)
            if prices:
                unique_prices = []
                seen = set()
                for price in prices:
                    clean = re.sub(r"\s+", "", price)
                    if clean not in seen:
                        unique_prices.append(clean)
                        seen.add(clean)
                if unique_prices:
                    # Extraer contexto (nombre del curso)
                    course_names = ["Bots con Telegram", "Python para Ciencia", "Prompt Engineering"]
                    prices_with_context = []
                    for price in unique_prices[:5]:
                        for course in course_names:
                            if course.lower() in lowered:
                                prices_with_context.append(f"{course}: {price}")
                    
                    if prices_with_context:
                        return {"action": "reply", "message": "Según la base de conocimiento: " + "; ".join(prices_with_context) + ".", "mode": "offline"}
                    else:
                        return {"action": "reply", "message": "Según la base de conocimiento: " + "; ".join(unique_prices[:10]) + ".", "mode": "offline"}

        # Búsqueda de requisitos/prerequisitos
        if any(token in q for token in ["requisito", "prerrequisito", "necesita", "necesitas", "antes de empezar", "se requiere", "se necesita"]):
            for line in text.splitlines():
                if "prerrequisitos" in line.lower() or "requisitos" in line.lower() or "pre-requisito" in line.lower():
                    if len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}

        # Búsqueda de reembolso
        if any(token in q for token in ["reembolso", "devolucion", "cancelacion", "satisfecho", "refund", "dinero de vuelta", "recuperar dinero"]):
            if "garantia de reembolso" in lowered or "devolucion del 100%" in lowered or "si no quedas satisfecho" in lowered:
                return {
                    "action": "reply",
                    "message": "La política de garantía indica que puedes solicitar la devolución del 100% de tu dinero dentro de los primeros 7 días naturales tras el inicio del curso si no quedas satisfecho.",
                    "mode": "offline",
                }

        # Búsqueda de inscripción
        if any(token in q for token in ["inscrib", "matricula", "registro", "inicio", "fecha", "cohorte", "plazo", "como me inscribo", "enrolar"]):
            if "flujo del proceso de inscripcion" in lowered or "solicitud" in lowered or "seleccion" in lowered or "admisiones" in lowered:
                return {
                    "action": "reply",
                    "message": "El proceso de inscripción es: 1) Completar la solicitud, 2) Elegir cohorte y horario, 3) Realizar pago o adjuntar comprobante, 4) Confirmar validación, 5) Recibir acceso al LMS.",
                    "mode": "offline",
                }

        # Búsqueda de horarios
        if any(token in q for token in ["horario", "atencion", "atención", "soporte", "abierto", "horas", "cuando abren", "disponibilidad"]):
            for line in text.splitlines():
                if any(h in line.lower() for h in ["horarios de atencion", "horarios de atención", "atencion administrativa", "atención administrativa", "horario"]):
                    if len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}

        # Búsqueda de contenido/temario
        if any(token in q for token in ["contenido", "que aprendo", "temario", "modulo", "syllabus", "plan de estudio", "qué se enseña"]):
            matching_lines = self._best_matching_lines(question, text.splitlines())
            if matching_lines and any("módulo" in line.lower() or "temario" in line.lower() for line in matching_lines):
                combined = " ".join(matching_lines[:3])
                if len(combined) > 40:
                    return {"action": "reply", "message": combined, "mode": "offline"}

        # Búsqueda de modalidad
        if any(token in q for token in ["modalidad", "online", "presencial", "en vivo", "sincrónico", "asincrónico", "zoom", "lms"]):
            for line in text.splitlines():
                if any(m in line.lower() for m in ["modalidad", "online", "sincrónico", "asincrónico", "zoom", "lms"]):
                    if len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}

        # Búsqueda por líneas coincidentes como último recurso
        best_lines = self._best_matching_lines(question, text.splitlines())
        if best_lines:
            # Filtrar líneas muy cortas
            best_lines = [line for line in best_lines if len(line) > 25]
            if best_lines:
                combined = " ".join(best_lines[:3])
                if len(combined) > 40:
                    return {"action": "reply", "message": combined, "mode": "offline"}

        return {
            "action": "escalate",
            "message": "No tengo una respuesta exacta en la base de conocimiento. Puedes intentar reformular la pregunta o contactar con un asesor humano.",
            "mode": "offline",
        }

    def query(self, question: str) -> dict:
        normalized_q = question.strip().lower()
        if not normalized_q:
            return {"action": "escalate", "message": "Escribe una pregunta para empezar.", "mode": "offline"}
        if normalized_q in self.cache:
            return self.cache[normalized_q]

        if self.vector_store and GOOGLE_API_KEY and ChatGoogleGenerativeAI:
            try:
                docs = self.vector_store.similarity_search(question, k=3)
                context = "\n---\n".join(doc.page_content for doc in docs)

                last_error = None
                for model_name in GEMINI_CHAT_MODELS:
                    try:
                        llm = ChatGoogleGenerativeAI(
                            model=model_name,
                            temperature=0.1,
                            max_retries=0,
                        )
                        messages = [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
                        ]
                        response = llm.invoke(messages)
                        content = response.content.strip()

                        if "ESCALATE_TO_HUMAN" in content:
                            result = {
                                "action": "escalate",
                                "message": "Lo siento, no tengo esa información exacta en mi base de conocimientos. Un asesor humano te contactará pronto.",
                                "mode": "gemini",
                            }
                        else:
                            result = {"action": "reply", "message": content, "mode": "gemini"}
                            self.cache[normalized_q] = result
                        return result
                    except Exception as exc:  # pragma: no cover
                        last_error = exc
                        msg = str(exc).lower()
                        if "429" in str(exc) or "quota" in msg or "resourceexhausted" in msg:
                            print(f"Gemini alcanzó cuota o límite: {exc}")
                        else:
                            print(f"Modelo Gemini {model_name} no disponible: {exc}")

                print(f"Ningún modelo Gemini disponible; usando fallback offline. Último error: {last_error}")
            except Exception as exc:  # pragma: no cover
                print(f"Gemini no disponible; usando fallback offline. Detalle: {exc}")

        # Fallback inmediato para evitar esperas largas cuando Gemini está agotado por cuota.
        docs = self._offline_search(question)
        result = self._offline_response(question, docs)
        self.cache[normalized_q] = result
        return result
