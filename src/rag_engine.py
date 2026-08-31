import os
import re

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
    "requisito": ["requisito", "prerrequisito", "preparacion", "preparación", "antes de empezar", "necesita", "necesitas"],
    "precio": ["precio", "cost", "costo", "cuanto", "cuánto", "pago", "descuento", "tarifa", "valor", "cuesta", "cuestan", "precio del curso"],
    "reembolso": ["reembolso", "devolucion", "devolución", "cancelacion", "cancelación", "refund", "satisfecho", "quedo satisfecho", "devolucion del 100%"],
    "inscripcion": ["inscrib", "matricula", "matrícula", "registro", "inicio", "horario", "fecha", "clases", "cuotas", "financiamiento", "plazo"],
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
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
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
        return re.sub(r"[^a-z0-9áéíóúñü\s]", " ", text.lower())

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
            for token in q_tokens:
                if token in text:
                    score += 2
            for category, aliases in SEARCH_ALIASES.items():
                if any(alias in normalized_question for alias in aliases):
                    if category in ["requisito", "precio", "reembolso", "inscripcion"]:
                        if any(alias in text for alias in aliases):
                            score += 5
            if score:
                scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:3]]

    def _offline_response(self, question: str, docs):
        if not docs:
            return {
                "action": "escalate",
                "message": "Todavía no tengo información suficiente en esta base de conocimiento para responderte. Puedes intentar otra pregunta o contactar con un asesor humano.",
                "mode": "offline",
            }

        text = "\n".join(doc.page_content for doc in docs)
        lowered = text.lower()
        q = self._normalize(question)

        topic_hits = {
            "precio": any(token in q for token in SEARCH_ALIASES["precio"]),
            "requisito": any(token in q for token in SEARCH_ALIASES["requisito"]),
            "reembolso": any(token in q for token in SEARCH_ALIASES["reembolso"]),
            "inscripcion": any(token in q for token in SEARCH_ALIASES["inscripcion"]),
        }

        if topic_hits["precio"]:
            prices = re.findall(r"\$\d+\s*USD|\$\d+", text)
            if prices:
                return {"action": "reply", "message": "Según la base de conocimiento: " + "; ".join(prices) + ".", "mode": "offline"}

        if topic_hits["requisito"]:
            match = re.search(r"prerrequisitos?:?[^\n]*\n?[^\n]*", text, flags=re.IGNORECASE)
            if match:
                return {"action": "reply", "message": match.group(0).strip(), "mode": "offline"}

            for line in text.splitlines():
                if "prerrequisitos" in line.lower() or "requisitos" in line.lower():
                    return {"action": "reply", "message": line.strip(), "mode": "offline"}

        if topic_hits["reembolso"]:
            if "garantía de reembolso" in lowered or "devolución del 100%" in lowered or "si no quedas satisfecho" in lowered:
                return {
                    "action": "reply",
                    "message": "La política indica que puedes solicitar la devolución del 100% de tu dinero dentro de los primeros 7 días naturales tras el inicio del curso si no quedas satisfecho.",
                    "mode": "offline",
                }

        if topic_hits["inscripcion"]:
            lines = [line.strip() for line in text.splitlines() if "pasos" in line.lower() or "fechas" in line.lower() or "inicio" in line.lower() or "matricul" in line.lower()]
            if lines:
                return {"action": "reply", "message": " ".join(lines[:3]), "mode": "offline"}

        if any(alias in q for alias in SEARCH_ALIASES["requisito"]):
            for line in text.splitlines():
                if "prerrequisitos" in line.lower() or "requisitos" in line.lower():
                    return {"action": "reply", "message": line.strip(), "mode": "offline"}

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
                        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.1)
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
                        print(f"Modelo Gemini {model_name} no disponible: {exc}")

                print(f"Ningún modelo Gemini disponible; usando fallback offline. Último error: {last_error}")
            except Exception as exc:  # pragma: no cover
                print(f"Gemini no disponible; usando fallback offline. Detalle: {exc}")

        docs = self._offline_search(question)
        result = self._offline_response(question, docs)
        self.cache[normalized_q] = result
        return result
