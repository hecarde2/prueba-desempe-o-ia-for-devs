# Docs — Sora AI

> **Documentación y conocimiento del negocio** — todo lo escrito.

Este directorio separa **lo que es papel** (markdown) de lo que es código (backend/frontend).

## Estructura

```
docs/
├── README.md                     # Este archivo — índice de docs
├── DOCUMENTACION_PROYECTO.md     # Doc técnica en español (20 secciones, 516 líneas)
├── DOCUMENTACION_PROYECTO_EN.md  # Doc técnica en inglés (515 líneas)
└── knowledge/
    └── base_conocimiento.md      # ÚNICA fuente de verdad del negocio (256 líneas, 9 secciones)
```

## Qué hay en cada archivo

- **knowledge/base_conocimiento.md:** La Academia. Contiene:
  1. Oferta académica (3 cursos + temario 5 módulos)
  2. Precios (tabla $150/$280/$160 + pronto pago + cuotas)
  3. Inscripción (5 pasos + calendario)
  4. Políticas (reembolso 7 días 100%, congelamiento 6 meses)
  5. Ecosistema (LMS/Discord)
  6. Soporte (horarios Lun-Vie 8-18, Sáb 9-13, mails, @SoporteAcademiaBot)
  7. Infra cloud (Colab, SageMaker, Docker)
  8. Mentorías y empleo (40 empresas, pasantías Scrum)
  9. Club I+D (GraphRAG, QLoRA, hackathons)
  → Es lo que lee `backend/rag_engine.py` y `backend/web_app.py` para responder y para la barra superior.

- **DOCUMENTACION_PROYECTO.md:** Documentación técnica completa en español: arquitectura, pipeline RAG, instalación, ejecución, API, seguridad, verificación, troubleshooting.

- **DOCUMENTACION_PROYECTO_EN.md:** Misma doc en inglés.

## Cómo editar

- Si cambia un precio o un horario, edita **solo** `docs/knowledge/base_conocimiento.md`. No toques código.
- Si cambia la arquitectura, edita `docs/DOCUMENTACION_PROYECTO.md`.

## Relación con el código

- `backend/rag_engine.py:87` busca primero `docs/knowledge`, luego `documents` (legacy) por compatibilidad.
- `backend/web_app.py:24` hace lo mismo para `/api/info`.
- `frontend/templates/index.html` muestra esa info en el slide-bar (cursos, precios, horarios...).

## Para junior

- **No confundas** `docs/` (documentación humana) con `venv/` (dependencias) o `frontend/` (visual).
- Todo lo que es “leer y escribir” está aquí. Todo lo que es “ejecutar” está en `backend/` y `frontend/`.
