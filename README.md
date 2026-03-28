# Lectorium

Plataforma web de clubes de lectura estructurados. Los usuarios se unen a grupos para leer un libro juntos, escriben reflexiones individuales, leen las de los demas y debaten en comunidad.

---

## Caracteristicas principales

- **Ciclo de vida completo** — Los clubes pasan automaticamente por fases: Abierto → Leyendo → Entrega → Revision → Debate → Cerrado
- **4 modos de verificacion de lectura** — Estricto, Moderado, Relajado y Libre
- **Debate en tiempo real** — Chat via WebSockets durante la fase de discusion
- **Reacciones e interacciones** — Like, interesante, de acuerdo, en desacuerdo en los reportes
- **Moderacion de contenido** — Sistema de flags para reportar contenido inapropiado
- **Busqueda de libros** — Integracion con Google Books API con fallback a base de datos local
- **Automatizacion** — Celery Beat transiciona las fases automaticamente segun fechas

---

## Stack tecnologico

| Capa | Tecnologia |
|---|---|
| Backend | Django 5.1 + DRF |
| Frontend | Django Templates + HTMX + Tailwind CSS (CDN) |
| Tiempo real | Django Channels + WebSockets (Daphne) |
| Base de datos | PostgreSQL 16 (psycopg v3) |
| Tareas / Scheduler | Celery 5 + django-celery-beat |
| Broker / Cache | Redis 7 |
| API externa | Google Books API |
| Deploy | Docker Compose + Nginx + Let's Encrypt |

---

## Requisitos previos

- Docker y Docker Compose
- Python 3.12 (solo para desarrollo local sin Docker)

---

## Instalacion rapida (Docker)

```bash
# 1. Clonar el repositorio
git clone https://github.com/tuusuario/lectorium.git
cd lectorium

# 2. Crear archivo de variables de entorno
cp .env.prod.example .env
# Editar .env con tus valores

# 3. Levantar servicios
docker compose up -d

# 4. Aplicar migraciones
docker compose exec web python manage.py migrate

# 5. Crear superusuario
docker compose exec web python manage.py createsuperuser

# 6. (Opcional) Cargar datos de prueba
docker compose exec web python manage.py seed
```

La aplicacion estara disponible en `http://localhost`.

---

## Instalacion local (sin Docker)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.prod.example .env
# Editar .env: apuntar DB_HOST=localhost, tener PostgreSQL y Redis corriendo

# Migraciones y servidor
python manage.py migrate
python manage.py runserver

# En terminales separadas:
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## Variables de entorno

Ver `.env.prod.example` para la lista completa. Las principales:

| Variable | Descripcion |
|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta de Django (cambiar en produccion) |
| `DJANGO_DEBUG` | `True` en desarrollo, `False` en produccion |
| `DJANGO_ALLOWED_HOSTS` | Dominios permitidos separados por coma |
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Conexion a PostgreSQL |
| `REDIS_URL` | URL de Redis para Channels |
| `CELERY_BROKER_URL` | URL de Redis para Celery |
| `GOOGLE_BOOKS_API_KEY` | API key de Google Books (opcional) |

---

## Estructura del proyecto

```
lectorium/
  config/               # Settings, URLs, ASGI, WSGI, Celery
  apps/
    accounts/           # Usuario personalizado, autenticacion, perfil
    books/              # Modelo Book, busqueda Google Books, registro manual
    clubs/              # Club, Membership, ciclo de vida, tareas Celery, WebSockets
    reports/            # Report, Reaction, Comment, DiscussionTopic, Verification, Flags
  templates/            # Templates Django (base, includes, por app)
  static/               # CSS, JS, imagenes estaticas
  nginx/                # Configuracion Nginx (dev y produccion)
  scripts/              # Scripts de mantenimiento (backups)
  .github/workflows/    # CI/CD con GitHub Actions
  docker-compose.yml    # Entorno de desarrollo
  docker-compose.prod.yml  # Entorno de produccion
```

---

## Fases del club

```
OPEN ──► READING ──► SUBMISSION ──► REVIEW ──► DISCUSSION ──► CLOSED
  │                                                               │
  └───────────────────── CANCELLED ◄─────────────────────────────┘
```

| Fase | Descripcion |
|---|---|
| **OPEN** | El club esta reclutando miembros |
| **READING** | Todos leen el libro (sin interacciones) |
| **SUBMISSION** | Cada quien entrega su reporte sin ver el de los demas |
| **REVIEW** | Se revelan los reportes; reacciones y propuesta de temas |
| **DISCUSSION** | Comentarios abiertos y debate en tiempo real |
| **CLOSED** | Club finalizado; cada autor ve solo su propio reporte |
| **CANCELLED** | Club cancelado (pocos miembros o decision del creador) |

Las transiciones son **100% automaticas** via Celery Beat cada 5 minutos.

---

## Modos de verificacion de lectura

| Modo | Requisito para debatir |
|---|---|
| **FREE** | Sin requisito |
| **RELAXED** | Confirmar "si termine el libro" |
| **MODERATE** | Responder preguntas del creador (el creador aprueba/rechaza) |
| **STRICT** | Haber entregado un reporte |

---

## Comandos utiles

```bash
# Datos de prueba (6 clubes en diferentes fases, 5 usuarios)
python manage.py seed
python manage.py seed --flush   # elimina datos existentes primero

# Tests
python manage.py test

# Shell de Django
python manage.py shell_plus     # requiere django-extensions

# Backup de base de datos (produccion)
./scripts/backup_postgres.sh
```

### Usuarios del seed

| Usuario | Password | Rol |
|---|---|---|
| `admin` | `lectorium123` | Superusuario |
| `user1` .. `user5` | `lectorium123` | Usuarios regulares |

---

## Deploy en produccion

Ver `docker-compose.prod.yml` y `nginx/prod.conf`. Pasos resumidos:

```bash
# 1. Copiar .env.prod.example como .env.prod y configurar
cp .env.prod.example .env.prod

# 2. Obtener certificado SSL inicial
docker compose -f docker-compose.prod.yml run --rm certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d tudominio.com --email tu@email.com --agree-tos

# 3. Reemplazar "tudominio.com" en nginx/prod.conf

# 4. Levantar en produccion
docker compose -f docker-compose.prod.yml up -d

# 5. Migraciones
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

La renovacion del certificado es automatica via el servicio `certbot`.

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) ejecuta en cada push a `main` o `develop`:

1. **Tests** — levanta PostgreSQL y Redis, corre `manage.py test`
2. **Lint** — revisa estilo con `flake8`

---

## Licencia

MIT
