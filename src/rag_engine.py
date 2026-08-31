import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS

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

class RAGEngine:
    def __init__(self, doc_dir: str = "documents"):
        self.doc_dir = doc_dir
        self.vector_store = None
        self.cache = {}
        self._init_vector_store()

    def _init_vector_store(self):
        documents = []
        if os.path.exists(self.doc_dir):
            for file in os.listdir(self.doc_dir):
                file_path = os.path.join(self.doc_dir, file)
                
                # Carga dinámica para archivos PDF y Markdown
                if file.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    documents.extend(loader.load())
                elif file.endswith(".md") or file.endswith(".txt"):
                    loader = TextLoader(file_path, encoding="utf-8")
                    documents.extend(loader.load())

        if not documents:
            print("Warning: No valid documents found in documents directory.")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        chunks = text_splitter.split_documents(documents)

        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        self.vector_store = FAISS.from_documents(chunks, embeddings)

    def query(self, question: str) -> dict:
        normalized_q = question.strip().lower()
        if normalized_q in self.cache:
            return self.cache[normalized_q]

        if not self.vector_store:
            return {
                "action": "escalate",
                "message": "Base de datos no inicializada. Un asesor humano te atenderá."
            }

        docs = self.vector_store.similarity_search(question, k=3)
        context = "\n---\n".join([doc.page_content for doc in docs])

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.1
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        if "ESCALATE_TO_HUMAN" in content:
            result = {
                "action": "escalate",
                "message": "Lo siento, no tengo esa información exacta en mi base de conocimientos. Un asesor humano te contactará pronto."
            }
        else:
            result = {
                "action": "reply",
                "message": content
            }
            self.cache[normalized_q] = result

        return result