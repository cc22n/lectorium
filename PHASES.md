# PHASES.md - Roadmap de desarrollo LectoriumMVP

## FASE 1 — Estructura base [COMPLETADA]
- [x] Proyecto Django con Docker Compose
- [x] Modelo de usuario personalizado (accounts.User)
- [x] 10 modelos de datos con relaciones y constraints
- [x] Admin configurado para todos los modelos
- [x] Configuracion Celery + Redis
- [x] ASGI preparado para Channels
- [x] Dockerfile + docker-compose.yml + nginx config
- [x] requirements.txt

## FASE 2 — Vistas basicas y auth [COMPLETADA]
- [x] Base template con Tailwind CDN + HTMX + navbar
- [x] Registro de usuarios
- [x] Login / logout
- [x] Perfil de usuario con clubes activos y reportes archivados
- [x] Editar perfil
- [x] Landing page con clubes abiertos
- [x] Explorar clubes con filtros (idioma, modo, status)
- [x] Detalle de club con info de fase y miembros
- [x] Crear club (formulario completo con busqueda de libro)
- [x] Busqueda de libros local con HTMX
- [x] Registro manual de libros
- [x] Unirse a un club con validaciones de limites
- [x] Abandonar club con reglas de fase
- [x] Transicion automatica OPEN->READING al alcanzar minimo

## FASE 3 — Ciclo completo del club [COMPLETADA]
Objetivo: que un club pueda completar todo su ciclo de vida.

### 3.1 Tareas Celery para transiciones automaticas
- [x] Tarea periodica que revise clubes y transicione segun fechas
- [x] OPEN timeout: si vence open_until con 5+ miembros pero sin alcanzar min_members, notificar al creador (3 dias para decidir)
- [x] OPEN timeout: si vence sin 5 miembros, cancelar
- [x] READING -> SUBMISSION automatico por fecha
- [x] SUBMISSION -> REVIEW automatico por fecha
- [x] REVIEW -> DISCUSSION automatico por fecha
- [x] DISCUSSION -> CLOSED automatico por fecha
- [x] Cancelacion automatica si miembros activos <= 3

### 3.2 Entrega de reportes (SUBMISSION)
- [x] Vista para escribir y entregar reporte
- [x] Validar que solo se puede entregar en fase SUBMISSION
- [x] Un reporte por usuario por club
- [x] No mostrar reportes de otros durante SUBMISSION

### 3.3 Revision de reportes (REVIEW)
- [x] Vista para ver todos los reportes del club
- [x] Sistema de reacciones (like, interesante, de_acuerdo, en_desacuerdo)
- [x] Proponer temas de debate
- [x] NO permitir comentarios en esta fase

### 3.4 Debate (DISCUSSION)
- [x] Comentarios en reportes
- [x] Chat en tiempo real con Django Channels + WebSockets
- [x] Mostrar temas propuestos como agenda
- [x] El creador puede cerrar debate antes de tiempo

### 3.5 Cierre del club (CLOSED)
- [x] Vista de club cerrado
- [x] Reportes propios visibles para cada autor
- [x] Debates no se conservan

## FASE 4 — Verificacion de lectura [COMPLETADA]
- [x] Modo STRICT: validar que usuario entrego reporte antes de permitir debate
- [x] Modo MODERATE: mostrar preguntas del creador, guardar respuestas, creador aprueba/rechaza
- [x] Modo RELAXED: confirmacion simple ("si termine el libro")
- [x] Modo FREE: sin validacion

## FASE 5 — Moderacion y flags [COMPLETADA]
- [x] Sistema de flags: reportar contenido inapropiado (reportes, comentarios, temas)
- [x] Vista para el creador del club para ver flags pendientes
- [x] Acciones del moderador: eliminar contenido flaggeado o desestimar flag
- [ ] Notificacion al usuario cuyo contenido fue eliminado (requiere modelo Notification, post-MVP)

## FASE 6 — Google Books API [COMPLETADA]
- [x] Integrar busqueda real con Google Books API (apps/books/services.py)
- [x] Guardar libros de la API en la base de datos local (save_google_book_view)
- [x] Mostrar portadas de libros en las cards (club_card.html + search_results.html)
- [x] Fallback a busqueda local si la API falla o no hay API key configurada
- [ ] Pendiente: agregar GOOGLE_BOOKS_API_KEY en .env (la variable existe, falta el valor)

## FASE 7 — Pulido y tests [COMPLETADA]
- [x] Tests unitarios para modelos (transiciones de fase, limites, membresias)
- [x] Tests de integracion para vistas (join, leave, submit report, reactions)
- [x] Tests para servicio Google Books (mock de API, deduplicacion)
- [x] Tests para logica de verificacion (user_can_discuss por modo)
- [x] Paginas 404 y 500 personalizadas (templates/404.html, templates/500.html)
- [x] Notificaciones Django messages ya funcionan (base.html las muestra)
- [x] Navbar responsive con menu hamburguesa para mobile
- [x] Accesibilidad basica: aria-label, aria-expanded en navbar mobile
- [x] Seed data: python manage.py seed (6 clubes en distintas fases, 5 usuarios)

## FASE 8 — Deploy [COMPLETADA]
- [x] Configurar Docker Compose para produccion (docker-compose.prod.yml)
- [x] Variables de entorno de produccion (.env.prod.example)
- [x] HTTPS con Let's Encrypt (nginx/prod.conf + certbot service)
- [x] Backups automaticos de PostgreSQL (scripts/backup_postgres.sh)
- [x] Monitoreo basico (health checks en todos los servicios)
- [x] CI/CD basico (.github/workflows/ci.yml con tests + lint)

---

## VERSION 2 (post-MVP)
Estas features quedan para despues de validar el MVP:
- Audio y speech-to-text para reportes
- IA para generar preguntas de verificacion de lectura
- IA para resumenes de discusiones
- Sistema de reputacion/gamificacion
- Chat privado entre usuarios
- Sistema social (seguir usuarios)
- Co-moderadores (1-2 adicionales con privilegios limitados)
- Normalizacion de autores como entidad separada
- Compartir reportes publicamente
- App movil
