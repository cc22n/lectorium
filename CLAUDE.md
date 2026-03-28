# CLAUDE.md - LectoriumMVP

## Que es este proyecto
Plataforma web de clubes de lectura estructurados. Los usuarios se unen a grupos para leer un libro, escriben reflexiones, leen las de otros y debaten ideas en comunidad.

## Stack tecnologico
- **Backend:** Django 5.1 + DRF
- **Frontend:** Django Templates + HTMX + Tailwind CSS (CDN)
- **Tiempo real:** Django Channels + WebSockets (solo para debate)
- **BD:** PostgreSQL (psycopg v3, NO psycopg2)
- **Tareas:** Celery + Redis
- **Cache/Broker:** Redis (compartido Celery + Channels)
- **API externa:** Google Books API (busqueda de libros)
- **Deploy futuro:** VPS + Docker Compose

## Estructura del proyecto
```
lectorium/
  config/           # Settings, URLs, ASGI, WSGI, Celery
  apps/
    accounts/       # Usuario personalizado, auth, perfil
    books/          # Modelo Book, busqueda, registro manual
    clubs/          # Club, Membership, ciclo de vida, vistas
    reports/        # Report, Reaction, Comment, DiscussionTopic, etc.
  templates/        # Django templates (base, includes, por app)
  static/           # CSS, JS, imagenes
  manage.py
  requirements.txt
  docker-compose.yml
  Dockerfile
```

## Comandos frecuentes
```bash
python manage.py runserver                    # Servidor dev
python manage.py makemigrations               # Crear migraciones
python manage.py migrate                      # Aplicar migraciones
python manage.py createsuperuser              # Crear admin
python manage.py test                         # Tests
celery -A config worker -l info               # Worker Celery
celery -A config beat -l info                 # Scheduler Celery
```

## Reglas criticas de desarrollo

### Python
- **Solo ASCII en archivos .py** — NO acentos, tildes, ni emojis en codigo Python. El entorno Windows/PowerShell no los maneja. Usar textos sin acentos o unicode escapes.
- Usar **psycopg v3** (no psycopg2). El import es `import psycopg`, el engine de Django es `django.db.backends.postgresql`.
- pip install siempre con `--break-system-packages` en el entorno local.

### Django
- AUTH_USER_MODEL = "accounts.User" (modelo custom, ya definido)
- Todas las apps estan en `apps/` con imports como `apps.accounts`, `apps.clubs`, etc.
- Settings usa python-dotenv parcrea cargar .env
- Zona horaria: America/Mexico_City
- Idioma por defecto: es (espanol)

### Frontend
- Tailwind via CDN (no compilado)
- HTMX para interacciones dinamicas sin JS pesado
- Diseno minimalista y limpio
- Fuentes: Source Serif 4 (headings) + DM Sans (body) via Google Fonts
- Colores: ink (#1a1a2e), parchment (#faf8f5), accent (#c7956d)
- Los templates usan herencia: base.html > page.html
- Componentes reutilizables en templates/includes/

### Modelo de datos (10 tablas)
1. **User** — extends AbstractUser (display_name, bio, avatar)
2. **Book** — titulo, autor, isbn, google_books_id, is_manual_entry
3. **Club** — nombre, libro, creador, modo, status, duraciones, fechas
4. **Membership** — user + club + role (CREATOR/MEMBER) + is_active
5. **Report** — reflexion del usuario sobre el libro del club
6. **Reaction** — like/interesante/de_acuerdo/en_desacuerdo en reportes
7. **Comment** — comentarios en reportes (solo fase DISCUSSION+)
8. **DiscussionTopic** — temas propuestos para debate (todos los modos)
9. **VerificationAnswer** — respuestas a preguntas del modo moderado
10. **ContentFlag** — reportes de contenido inapropiado

### Fases del club (maquina de estados)
```
OPEN -> READING -> SUBMISSION -> REVIEW -> DISCUSSION -> CLOSED
                                                      -> CANCELLED (desde cualquier fase)
```
- Transiciones 100% automaticas por fechas (Celery Beat)
- El creador solo puede cerrar debate antes de tiempo y moderar
- Si miembros activos <= 3 despues de OPEN: cancelacion automatica

### Modos del club
- **STRICT** — Reporte obligatorio para debatir
- **MODERATE** — Preguntas del creador para verificar lectura
- **RELAXED** — Confirmacion simple ("si termine el libro")
- **FREE** — Sin requisitos, debate abierto

### Limites de plataforma
- Max 3 clubes activos por usuario (creados + unidos)
- Max 2 clubes creados por usuario
- Min 5 miembros obligatorio por club
- Max 20-25 miembros por club
- Si no se alcanza minimo al vencer OPEN: 3 dias para que creador decida
- Umbral de cancelacion: 3 miembros activos o menos

### Reglas de fases
- **SUBMISSION:** cada quien entrega reporte sin ver los de otros
- **REVIEW:** se revelan reportes, se puede reaccionar y proponer temas, NO comentar
- **DISCUSSION:** se abren comentarios y debate en tiempo real
- **CLOSED:** solo reportes propios quedan visibles para el autor
- Debates NO se conservan despues del cierre

## Lo que ya esta implementado (Fases 1 y 2)
- Estructura del proyecto Django + Docker Compose
- 10 modelos de datos con relaciones y constraints
- Admin configurado para todos los modelos
- Configuracion Celery + Redis lista
- ASGI preparado para WebSockets
- Templates: base, navbar, landing, explorar, detalle club, crear club, login, registro, perfil, editar perfil
- Busqueda de libros (local) con HTMX + registro manual
- Crear club con formulario completo
- Unirse/abandonar clubes con validaciones
- Transicion automatica OPEN->READING cuando se alcanza minimo
- Filtros de exploracion (idioma, modo, status)
- Paginacion

## Lo que falta para completar el MVP
Ver archivo PHASES.md para detalle completo.
