# Frontend — Sora AI

> **Interfaz visual de Sora** — lo que ve el usuario.

Este directorio contiene **todo lo que es visual** (HTML/CSS/JS). Está separado del backend para que sea fácil de encontrar y editar sin tocar lógica de IA.

## Estructura

```
frontend/
├── templates/
│   └── index.html          # HTML principal (Jinja2) — layout sidebar + chat
└── static/
    ├── css/
    │   └── style.css       # Estilos completos (variables light/dark, responsive)
    └── js/
        └── app.js          # Lógica del chat, tema, tamaño letra, sidebar
```

## Tecnologías

- **HTML5** semántico + `Jinja2` (`{{ url_for('static', ...) }}`)
- **CSS3** con variables (`--bg`, `--panel`, `--text`, `--font-scale`) para tema claro/oscuro
- **Vanilla JS** (sin frameworks) — `fetch` a `/api/*`, `localStorage` para preferencias

## Características de UX

- **Sidebar slide-bar** (360px) con información rápida: cursos, precios, horarios, inscripción 5 pasos, garantía 7 días. En móvil es overlay con `☰` hamburger.
- **Tema claro / oscuro** — botón en sidebar y topbar, guarda en `localStorage sora-theme`, usa `data-theme` en `<html>`.
- **Tamaño de letra** — slider 85%–130% + botones A-/A+ (`--font-scale` en `html`), guarda en `sora-font`.
- **Densidad** — Cómodo / Compacto (`data-density`), guarda en `sora-density`.
- **Otros** — animaciones on/off, `Ctrl+B` para sidebar, `Esc` para cerrar, `Enter` para enviar.

## Cómo editar

- Cambia colores en `frontend/static/css/style.css` → `:root` y `[data-theme="light"]`.
- Cambia lógica en `frontend/static/js/app.js` → `renderSidebarInfo()`, `sendMessage()`, `applyTheme()`.
- No toques `backend/` si solo quieres ajustar la UI.

## Conexión con backend

- `GET /` → `backend/web_app.py:19` renderiza `frontend/templates/index.html`
- `GET /static/...` → Flask sirve `frontend/static/...` (configurado como `static_folder`)
- `GET /api/info` y `POST /api/chat` → el JS hace `fetch` y pinta la respuesta en `.chat`

## Probar solo el frontend

```bash
# Sin backend, solo abre el HTML (sin datos dinámicos):
open frontend/templates/index.html
# Con backend (recomendado):
python main.py  # http://localhost:5002
```
