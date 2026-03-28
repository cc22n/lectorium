# Skill: Seguridad — Patrones del proyecto

## Autenticacion
- Modelo custom: `accounts.User` (extiende AbstractUser)
- Django auth built-in para login/logout/register
- `@login_required` en toda vista que necesite auth
- LOGIN_URL = "accounts:login"
- Passwords: validadores de Django por defecto (minimo 8 chars, no comunes, etc.)

## Autorizacion por roles
El sistema tiene roles a nivel de club, no globales:
- **CREATOR:** puede moderar, cerrar debate, ver flags
- **MEMBER:** puede participar segun las reglas del modo del club

### Verificar permisos en vistas
```python
# Verificar que es miembro activo
membership = club.memberships.filter(user=request.user, is_active=True).first()
if not membership:
    messages.error(request, "No eres miembro.")
    return redirect(...)

# Verificar que es creador
if membership.role != MemberRole.CREATOR:
    messages.error(request, "Solo el creador puede hacer esto.")
    return redirect(...)

# Verificar fase del club
if club.status != ClubStatus.SUBMISSION:
    messages.error(request, "No es momento de entregar reportes.")
    return redirect(...)
```

## CSRF
- Todos los formularios POST incluyen `{% csrf_token %}`
- HTMX envia CSRF automaticamente via `hx-headers` en base.html:
  ```html
  <body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  ```

## Validacion de datos
- SIEMPRE validar en el servidor, nunca confiar en el cliente
- Usar Django Forms para validacion
- Verificar limites de plataforma antes de crear/unirse:
  - `user.can_create_club()` antes de crear
  - `user.can_join_club()` antes de unirse
  - `club.can_accept_members()` antes de aceptar

## Proteccion de datos
- Reportes de otros usuarios solo visibles en fases REVIEW+
- Reportes solo visibles para miembros del club (y el autor despues del cierre)
- Debates no se conservan despues de CLOSED
- Informacion de perfil: solo display_name y bio son publicos

## Reglas de on_delete
- `Club.book` -> PROTECT (no borrar libro si tiene clubes)
- `Club.creator` -> PROTECT (no borrar usuario si creo clubes)
- `Membership.user` -> CASCADE
- `Membership.club` -> CASCADE
- `Report.user` -> CASCADE
- `Book.created_by` -> SET_NULL

## Sanitizacion
- Django auto-escapa HTML en templates por defecto
- No usar `|safe` filter a menos que sea absolutamente necesario
- Para texto de usuario (reportes, comentarios, descripciones) dejar que Django escape

## Rate limiting (futuro)
- No implementado en MVP
- Para v2: considerar django-ratelimit en endpoints criticos (register, login, crear club)
