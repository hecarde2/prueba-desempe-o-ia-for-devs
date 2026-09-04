import concurrent.futures
import os
import re
import time
import unicodedata

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_EMBEDDING_MODEL

try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    # Parchear el retry de Gemini para que el fallback offline sea inmediato y no espere 60s por cuota.
    try:
        import langchain_google_genai.chat_models as _chat_models
        from tenacity import stop_after_attempt, retry

        def _fast_retry_decorator():
            # Solo 1 intento, sin reintentos exponenciales, para que el fallback offline sea rápido.
            return retry(reraise=True, stop=stop_after_attempt(1))

        _chat_models._create_retry_decorator = _fast_retry_decorator
    except Exception:
        pass
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

STOPWORDS = {
    "el","la","los","las","de","del","en","y","a","con","que","es","para","por","un","una","al","le","lo","se","su","sus","me","te","nos","os","si","no","mi","tu","su","ya","aun","aún","tambien","también","solo","sólo","hay","son","ser","estar","haber","tener","hacer","ir","venir","decir","dar","saber","querer","poder","deber","todo","todos","mucho","poco","muy","mas","menos","pero","aunque","sino","pues","entonces","cuando","donde","como","porque","esta","este","esto","esa","ese","aquella","aquel","aquí","allí","allí","vez","veces","quien","cual","quienes","cuales","usted","ustedes","yo","tu","el","ella","nosotros","vosotros","ellos","ellas","les","las","los","nos","os","me","te","se","uno","dos","tres","ese","esa","eso","aqui","alli","hoy","ahora","despues","después","antes","durante","siempre","nunca","tambien","ademas","además","sobre","entre","hasta","desde","sin","bajo","tras","durante","mediante","según","segun","cada","otro","otra","otros","otras","mismo","misma","mismos","mismas","tan","tanto","mientras","aunque","sino","sino","cual","como","cuanto","cuanta","cuantos","cuantas","quien","quienes","donde","cuando","porque","para","por","ahi","ahí",
    "hola","gracias","por","favor","buenos","dias","tardes","noches","saludos","hey","holi","chau","adios","adiós"
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
    "gemini-flash-latest",
]
GEMINI_EMBEDDING_MODELS = [
    GEMINI_EMBEDDING_MODEL,
    "models/gemini-embedding-001",
    "models/gemini-embedding-2",
]


class RAGEngine:
    def __init__(self, doc_dir: str = "documents"):
        self.doc_dir = doc_dir
        self.vector_store = None
        self.raw_documents = []
        self.cache = {}
        self._quota_blocked_until = 0  # timestamp para circuit breaker de Gemini (chat)
        self._embed_blocked_until = 0  # circuit breaker para embeddings
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
                # si embeddings bloqueado por cuota, no intentar
                if time.time() < self._embed_blocked_until:
                    print("Embeddings bloqueado por cuota reciente, usando modo offline.")
                    break
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model=model_name,
                        request_options={"timeout": 5},
                    )
                    self.vector_store = FAISS.from_documents(chunks, embeddings)
                    print(f"Vector store inicializado con {model_name} ({len(chunks)} chunks).")
                    return
                except Exception as exc:  # pragma: no cover
                    msg = str(exc).lower()
                    if "429" in str(exc) or "quota" in msg or "resourceexhausted" in msg:
                        print(f"Embeddings {model_name} cuota excedida: {exc}")
                        self._embed_blocked_until = time.time() + 60
                    else:
                        print(f"Embeddings {model_name} no disponible: {exc}")

            self.vector_store = None
            if time.time() < self._embed_blocked_until:
                print("Vector DB en modo offline por cuota de embeddings.")
        except Exception as exc:  # pragma: no cover
            print(f"Vector DB no disponible; usando modo offline. Detalle: {exc}")
            self.vector_store = None

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize('NFKD', text.lower())
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9\s]", " ", normalized)

    def _filtered_tokens(self, normalized_text: str):
        tokens = normalized_text.split()
        return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]

    def _offline_search(self, question: str):
        if not self.raw_documents:
            return []

        normalized_question = self._normalize(question)
        q_tokens = self._filtered_tokens(normalized_question)
        if not q_tokens:
            # if all tokens are stopwords, keep original but filter short
            q_tokens = [t for t in normalized_question.split() if len(t) > 2]
            if not q_tokens:
                return []

        scored = []
        for document in self.raw_documents:
            text = self._normalize(document.page_content)
            score = 0

            # Puntuación por tokens filtrados
            for token in q_tokens:
                if token in text:
                    score += 3
                # bonus for exact word boundary
                if re.search(rf"\b{re.escape(token)}\b", text):
                    score += 2

            # Puntuación por aliases de categoría (usando normalized)
            for category, aliases in SEARCH_ALIASES.items():
                matching_aliases_q = [alias for alias in aliases if self._normalize(alias) in normalized_question]
                if matching_aliases_q:
                    matching_aliases_doc = [alias for alias in aliases if self._normalize(alias) in text]
                    if matching_aliases_doc:
                        score += len(matching_aliases_q) * len(matching_aliases_doc) * 2

            if score:
                scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:5]]

    def _best_matching_lines(self, question: str, lines, min_score: int = 6):
        normalized_question = self._normalize(question)
        q_tokens = self._filtered_tokens(normalized_question)
        # if filtered empty, use all non-stopword short tokens
        if not q_tokens:
            q_tokens = [t for t in normalized_question.split() if len(t) > 2]
        tokens_set = set(q_tokens)
        if not tokens_set:
            return []

        scored = []

        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 12:
                continue
            # skip markdown separators
            if re.match(r"^\s*\|?\s*[:\-\|]+\s*$", stripped):
                continue
            normalized_line = self._normalize(stripped)
            line_tokens = set(self._filtered_tokens(normalized_line))
            if not line_tokens:
                continue
            score = 0

            # token overlap
            overlap = tokens_set.intersection(set(normalized_line.split()))
            for token in overlap:
                if len(token) > 3:
                    score += 5
                else:
                    score += 2

            # bonus for phrase overlap
            for token in tokens_set:
                if token in normalized_line:
                    # already counted but extra for exact
                    pass

            # penalizar líneas muy genéricas sin números ni palabras clave
            if len(stripped) < 25:
                score = int(score * 0.6)

            if score >= min_score:
                scored.append((score, stripped))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [line for _, line in scored[:6]]

    def _extract_prices_table(self, text: str):
        """Parse markdown table for course prices. Returns list of dicts."""
        courses = []
        # find table rows with | **Course** | $X USD ...
        # Each row: | **Name** | $150 USD | $120 USD | 2 x $75 USD | ...
        pattern = re.compile(r"\|\s*\*\*(.+?)\*\*\s*\|\s*\$\s*(\d+)\s*USD\s*\|\s*\$\s*(\d+)\s*USD\s*\|\s*([^|]+)\|\s*([^|]+)\|")
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            regular = match.group(2).strip()
            pronto = match.group(3).strip()
            cuotas2 = match.group(4).strip()
            cuotas3 = match.group(5).strip()
            courses.append({
                "name": name,
                "regular": f"${regular} USD",
                "pronto": f"${pronto} USD",
                "cuotas2": cuotas2,
                "cuotas3": cuotas3,
            })
        # fallback simpler: just capture name and regular price
        if not courses:
            simple_pat = re.compile(r"\*\*\s*([^*]+?)\s*\*\*\s*\|\s*\$(\d+)\s*USD")
            for m in simple_pat.finditer(text):
                courses.append({"name": m.group(1).strip(), "regular": f"${m.group(2)} USD", "pronto": "", "cuotas2": "", "cuotas3": ""})
        return courses

    def _offline_response(self, question: str, docs):
        if not docs and not self.raw_documents:
            return {
                "action": "escalate",
                "message": "Todavía no tengo información suficiente en esta base de conocimiento para responderte. Puedes intentar otra pregunta o contactar con un asesor humano.",
                "mode": "offline",
            }

        text = "\n".join(doc.page_content for doc in (docs or self.raw_documents))
        q = self._normalize(question)
        q_tokens_filtered = self._filtered_tokens(q)
        text_normalized = self._normalize(text)
        lowered = text.lower()

        # --- Saludo / greeting (no escalar en offline) ---
        greetings = {"hola","hello","hey","buenas","buenos dias","buenas tardes","buenas noches","saludos","hi","holi"}
        if q.strip() in greetings or any(g == q.strip() for g in greetings):
            return {"action": "reply", "message": "¡Hola! Soy Sora, la asistente virtual de la Academia de Tecnología e IA. ¿En qué te puedo ayudar hoy sobre cursos, horarios, precios, inscripciones o reembolsos?", "mode": "offline"}
        # si pregunta es muy corta y es saludo extendido
        if len(q_tokens_filtered) == 1 and q_tokens_filtered[0] in {"hola","hello","hey","saludos","buenas"}:
            return {"action": "reply", "message": "¡Hola! Soy Sora, la asistente virtual de la Academia de Tecnología e IA. ¿En qué te puedo ayudar hoy sobre cursos, horarios, precios, inscripciones o reembolsos?", "mode": "offline"}

        # --- Búsqueda de precios (prioridad alta) ---
        price_triggers = ["cuanto","precio","costo","descuento","tarifa","valor","cuesta","arancel","inversion","quanto","coste"]
        if any(tok in q for tok in price_triggers):
            courses = self._extract_prices_table(text)
            if courses:
                # si pregunta menciona curso específico, filtrar
                q_lower_simple = question.lower()
                filtered = []
                for c in courses:
                    # check partial name match: bots, python, prompt
                    name_low = c["name"].lower()
                    if "bots" in q_lower_simple or "telegram" in q_lower_simple:
                        if "bots" in name_low or "telegram" in name_low:
                            filtered.append(c)
                    elif "python" in q_lower_simple or "ciencia" in q_lower_simple or "data" in q_lower_simple:
                        if "python" in name_low:
                            filtered.append(c)
                    elif "prompt" in q_lower_simple or "agentes" in q_lower_simple:
                        if "prompt" in name_low:
                            filtered.append(c)
                target = filtered if filtered else courses
                if len(target) == 1:
                    c = target[0]
                    parts = [f"{c['name']}: {c['regular']}"]
                    if c.get("pronto"):
                        parts.append(f"pronto pago {c['pronto']} (hasta el 20)")
                    if c.get("cuotas2"):
                        parts.append(f"2 cuotas {c['cuotas2']}")
                    return {"action": "reply", "message": "Según la base de conocimiento: " + " | ".join(parts) + ".", "mode": "offline"}
                else:
                    price_list = []
                    for c in target[:3]:
                        price_list.append(f"{c['name']}: {c['regular']}")
                    return {"action": "reply", "message": "Según la base de conocimiento, los precios son: " + "; ".join(price_list) + ".", "mode": "offline"}
            # fallback if table parse failed but prices exist
            prices = re.findall(r"\$\s*\d+(?:\.\d+)?\s*USD", text, flags=re.IGNORECASE)
            if prices:
                unique = []
                seen = set()
                for p in prices:
                    clean = re.sub(r"\s+", " ", p.strip())
                    clean = re.sub(r"\s+", "", clean) if "USD" not in clean else clean  # keep format
                    # normalize
                    clean_norm = re.sub(r"\s+", " ", p).strip()
                    if clean_norm not in seen:
                        unique.append(clean_norm)
                        seen.add(clean_norm)
                if unique:
                    return {"action": "reply", "message": "Según la base de conocimiento: " + "; ".join(unique[:6]) + ".", "mode": "offline"}

        # --- Búsqueda de requisitos/prerequisitos ---
        req_triggers = ["requisito","prerrequisito","necesita","necesitas","antes de empezar","se requiere","se necesita","prerequisito","conocimientos previos"]
        if any(t in q for t in req_triggers):
            # buscar líneas con prerrequisitos en texto original
            for line in text.splitlines():
                low = line.lower()
                if "prerrequisitos" in low or "pre-requisito" in low:
                    if len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}
            # fallback: buscar con normalize
            for line in text.splitlines():
                if "prerrequisitos" in self._normalize(line):
                    if len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}

        # --- Búsqueda de reembolso ---
        reembolso_triggers = ["reembolso","devolucion","cancelacion","satisfecho","refund","dinero de vuelta","recuperar dinero","garantia"]
        if any(t in q for t in reembolso_triggers):
            # texto normalizado contiene garantía y 7 dias
            if ("garantia" in text_normalized and "7 dias" in text_normalized) or ("reembolso" in text_normalized and "7 dias" in text_normalized) or ("devolucion" in text_normalized and "100" in text_normalized):
                return {
                    "action": "reply",
                    "message": "La política de garantía indica que puedes solicitar la devolución del 100% de tu dinero dentro de los primeros 7 días naturales tras el inicio del curso si no quedas satisfecho.",
                    "mode": "offline",
                }
            # fallback por líneas
            for line in text.splitlines():
                if "garantia de satisfaccion" in self._normalize(line) or "garantia de satisfacción" in line.lower():
                    if len(line.strip()) > 10:
                        # buscar siguiente línea con 7 días
                        idx = text.splitlines().index(line)
                        context = " ".join(text.splitlines()[idx: idx+4])
                        if "7 días" in context or "7 dias" in self._normalize(context):
                            return {"action": "reply", "message": "La política de garantía indica que puedes solicitar la devolución del 100% de tu dinero dentro de los primeros 7 días naturales tras el inicio del curso si no quedas satisfecho.", "mode": "offline"}

        # --- Búsqueda de inscripción ---
        inscrip_triggers = ["inscrib","matricula","registro","cohorte","plazo","como me inscribo","enrolar","admision"]
        if any(t in q for t in inscrip_triggers):
            if "flujo del proceso de inscripcion" in text_normalized or "proceso de inscripcion" in text_normalized:
                return {
                    "action": "reply",
                    "message": "El proceso de inscripción es: 1) Completar la solicitud, 2) Elegir cohorte y horario, 3) Realizar pago o adjuntar comprobante, 4) Confirmar validación, 5) Recibir acceso al LMS.",
                    "mode": "offline",
                }

        # --- Búsqueda de duración ---
        duracion_triggers = ["duracion","semanas","horas lectivas","cuanto dura","cuando termina","duracion del curso"]
        if any(t in q for t in duracion_triggers):
            # buscar líneas con duración
            for line in text.splitlines():
                low = line.lower()
                if "duración" in low or "duracion" in self._normalize(low):
                    if "semanas" in low and "horas" in low and len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}
            # fallback best lines con duración
            dur_lines = self._best_matching_lines(question, text.splitlines(), min_score=5)
            dur_filtered = [l for l in dur_lines if "semana" in l.lower() or "duración" in l.lower() or "duracion" in self._normalize(l)]
            if dur_filtered:
                return {"action": "reply", "message": " ".join(dur_filtered[:2]), "mode": "offline"}

        # --- Búsqueda de certificado ---
        cert_triggers = ["certificado","diploma","constancia","acreditacion","titulacion","credenciales"]
        if any(t in q for t in cert_triggers):
            # buscar sección de certificación
            for line in text.splitlines():
                low = line.lower()
                if "certificación" in low or "certificacion" in self._normalize(low) or "certificado" in low:
                    if len(line.strip()) > 15:
                        # tomar contexto 3 líneas
                        idx = text.splitlines().index(line)
                        context = " ".join([l.strip() for l in text.splitlines()[idx: idx+4] if l.strip()])
                        if len(context) > 30:
                            return {"action": "reply", "message": context[:500], "mode": "offline"}
            cert_lines = self._best_matching_lines(question, text.splitlines(), min_score=5)
            if cert_lines:
                return {"action": "reply", "message": " ".join(cert_lines[:3]), "mode": "offline"}

        # --- Búsqueda de horarios (prioridad alta) ---
        horario_triggers = ["horario","atencion","cuando abren","disponibilidad","horarios de atencion"]
        # distinguir "horas" genérico de horario atención: solo si pregunta contiene horario/atención
        if any(t in q for t in horario_triggers):
            # extraer con regex específico
            m = re.search(r"Atención Administrativa y Soporte:\*\*\s*([^\n]+)", text)
            if m:
                horario = m.group(1).strip()
                # limpiar asteriscos
                horario = horario.strip("* ").strip()
                if len(horario) > 10:
                    return {"action": "reply", "message": f"Horario de atención: {horario}", "mode": "offline"}
            # fallback buscar líneas con Lunes a Viernes
            for line in text.splitlines():
                if "lunes a viernes" in line.lower() and "gmt-5" in line.lower():
                    return {"action": "reply", "message": line.strip(), "mode": "offline"}
            m2 = re.search(r"Lunes a Viernes[^\n]+GMT-5[^\n]*", text, flags=re.IGNORECASE)
            if m2:
                return {"action": "reply", "message": m2.group(0).strip(), "mode": "offline"}

        # --- Búsqueda de contenido/temario ---
        contenido_triggers = ["contenido","temario","modulo","syllabus","plan de estudio","que aprendo","que se ensena","perfil de egreso","que voy a aprender"]
        if any(t in q for t in contenido_triggers):
            matching_lines = self._best_matching_lines(question, text.splitlines(), min_score=5)
            # filtrar que contengan módulo o temario
            filtered = [l for l in matching_lines if "módulo" in l.lower() or "modulo" in self._normalize(l) or "temario" in l.lower()]
            if filtered:
                combined = " ".join(filtered[:3])
                if len(combined) > 40:
                    return {"action": "reply", "message": combined, "mode": "offline"}
            if matching_lines:
                combined = " ".join(matching_lines[:3])
                if len(combined) > 40:
                    return {"action": "reply", "message": combined, "mode": "offline"}

        # --- Búsqueda de modalidad ---
        modalidad_triggers = ["modalidad","online","presencial","en vivo","sincronico","asincronico","zoom","lms"]
        if any(t in q for t in modalidad_triggers):
            # buscar líneas con modalidad
            for line in text.splitlines():
                low = line.lower()
                if "modalidad" in low and len(line.strip()) > 15:
                    return {"action": "reply", "message": line.strip(), "mode": "offline"}
            # buscar online con contexto
            for line in text.splitlines():
                if any(k in line.lower() for k in ["online", "sincrónico", "asincrónico", "zoom"]):
                    if "modalidad" in text_normalized and len(line.strip()) > 15:
                        return {"action": "reply", "message": line.strip(), "mode": "offline"}

        # --- Búsqueda por líneas coincidentes como último recurso ---
        best_lines = self._best_matching_lines(question, text.splitlines(), min_score=5)
        if best_lines:
            best_lines = [line for line in best_lines if len(line) > 25]
            if best_lines:
                # verificar que al menos un token filtrado importante aparece
                if any(tok in self._normalize(" ".join(best_lines[:2])) for tok in q_tokens_filtered):
                    combined = " ".join(best_lines[:3])
                    if len(combined) > 40:
                        return {"action": "reply", "message": combined, "mode": "offline"}

        # Si no hay tokens relevantes, escalar
        # Verificar si pregunta tiene overlap mínimo con documento
        if not q_tokens_filtered:
            return {
                "action": "escalate",
                "message": "No tengo una respuesta exacta en la base de conocimiento. Puedes intentar reformular la pregunta o contactar con un asesor humano.",
                "mode": "offline",
            }
        # si ningún token filtrado aparece en el texto, escalar directamente
        if not any(tok in text_normalized for tok in q_tokens_filtered):
            return {
                "action": "escalate",
                "message": "Lo siento, esa consulta está fuera del alcance de mi base de conocimiento. Un asesor humano te contactará pronto.",
                "mode": "offline",
            }

        return {
            "action": "escalate",
            "message": "No tengo una respuesta exacta en la base de conocimiento. Puedes intentar reformular la pregunta o contactar con un asesor humano.",
            "mode": "offline",
        }

    def _gemini_attempt(self, question: str) -> dict | None:
        """Intento único de Gemini con timeout controlado. Retorna dict si tuvo éxito, None si debe hacer fallback."""
        # si embeddings bloqueados, no intentar similarity_search
        if time.time() < self._embed_blocked_until:
            raise RuntimeError("Embeddings bloqueado por cuota")

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
                    return {
                        "action": "escalate",
                        "message": "Lo siento, no tengo esa información exacta en mi base de conocimientos. Un asesor humano te contactará pronto.",
                        "mode": "gemini",
                    }
                return {"action": "reply", "message": content, "mode": "gemini"}

            except Exception as exc:  # pragma: no cover
                last_error = exc
                msg = str(exc).lower()
                if "429" in str(exc) or "quota" in msg or "resourceexhausted" in msg:
                    print(f"Gemini alcanzó cuota o límite: {exc}")
                    self._quota_blocked_until = time.time() + 60
                    # en cuota, no probar más modelos, ir directo a offline
                    raise RuntimeError(f"Quota excedida en {model_name}") from exc
                # error de modelo (404) → probar siguiente rápido
                print(f"Modelo Gemini {model_name} no disponible: {exc}")

        if last_error:
            raise last_error
        return None

    def query(self, question: str) -> dict:
        normalized_q = question.strip().lower()
        if not normalized_q:
            return {"action": "escalate", "message": "Escribe una pregunta para empezar.", "mode": "offline"}
        if normalized_q in self.cache:
            return self.cache[normalized_q]

        # Circuit breaker: si Gemini está bloqueado por cuota, ir directo a offline (ultra rápido)
        use_gemini = bool(self.vector_store and GOOGLE_API_KEY and ChatGoogleGenerativeAI)
        if use_gemini and time.time() < self._quota_blocked_until:
            use_gemini = False
        if use_gemini and time.time() < self._embed_blocked_until:
            use_gemini = False

        if use_gemini:
            try:
                # Timeout total de 2.5s para todo el intento Gemini (embedding + LLM)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._gemini_attempt, question)
                    try:
                        result = future.result(timeout=2.5)
                        if result:
                            self.cache[normalized_q] = result
                            return result
                    except concurrent.futures.TimeoutError:
                        print("Gemini timeout (2.5s), usando fallback offline")
                        self._quota_blocked_until = time.time() + 30
                        # cancelar tarea en background
                        future.cancel()
            except RuntimeError as exc:
                # quota ya manejada, ir a offline
                msg = str(exc).lower()
                if "429" in msg or "quota" in msg or "embeddings bloqueado" in msg:
                    self._quota_blocked_until = time.time() + 60
                # no reintentar, caer a offline
                pass
            except Exception as exc:  # pragma: no cover
                msg = str(exc).lower()
                if "429" in str(exc) or "quota" in msg or "resourceexhausted" in msg:
                    self._quota_blocked_until = time.time() + 60
                # errores de embedding también bloquean
                if "embed" in msg and ("429" in msg or "quota" in msg):
                    self._embed_blocked_until = time.time() + 60
                print(f"Gemini no disponible; usando fallback offline. Detalle: {exc}")

        # Fallback inmediato y rápido (< 5ms)
        docs = self._offline_search(question)
        result = self._offline_response(question, docs)
        self.cache[normalized_q] = result
        return result

