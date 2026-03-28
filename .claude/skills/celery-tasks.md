# Skill: Celery — Tareas y transiciones de fase

## Configuracion
- Broker: Redis (redis://localhost:6379/1 para dev)
- Scheduler: django_celery_beat (DatabaseScheduler)
- App Celery definida en config/celery.py
- Autodiscover busca tasks.py en cada app

## Tarea principal: check_club_transitions
Esta tarea se ejecuta periodicamente (cada 5-10 minutos) y revisa todos los clubes que necesitan transicionar de fase.

```python
# apps/clubs/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Club, ClubStatus

@shared_task
def check_club_transitions():
    """Revisa y ejecuta transiciones de fase automaticas."""
    now = timezone.now()

    # OPEN -> timeout
    open_clubs = Club.objects.filter(
        status=ClubStatus.OPEN,
        open_until__lte=now,
    )
    for club in open_clubs:
        handle_open_timeout(club, now)

    # READING -> SUBMISSION
    reading_clubs = Club.objects.filter(
        status=ClubStatus.READING,
        submission_starts_at__lte=now,
    )
    for club in reading_clubs:
        club.transition_to(ClubStatus.SUBMISSION)

    # SUBMISSION -> REVIEW
    submission_clubs = Club.objects.filter(
        status=ClubStatus.SUBMISSION,
        review_starts_at__lte=now,
    )
    for club in submission_clubs:
        club.transition_to(ClubStatus.REVIEW)

    # REVIEW -> DISCUSSION
    review_clubs = Club.objects.filter(
        status=ClubStatus.REVIEW,
        discussion_starts_at__lte=now,
    )
    for club in review_clubs:
        club.transition_to(ClubStatus.DISCUSSION)

    # DISCUSSION -> CLOSED
    discussion_clubs = Club.objects.filter(
        status=ClubStatus.DISCUSSION,
        closes_at__lte=now,
    )
    for club in discussion_clubs:
        club.transition_to(ClubStatus.CLOSED)
```

## Logica del timeout de OPEN
```python
def handle_open_timeout(club, now):
    if club.active_members_count < 5:
        # Menos del minimo de plataforma: cancelar
        club.cancel(reason="No alcanzo minimo de 5 miembros")
    elif club.active_members_count < club.min_members:
        # Tiene 5+ pero no el minimo del creador
        # Dar 3 dias al creador para decidir
        # Esto requiere un campo adicional o una tarea delayed
        # Por ahora: si han pasado 3 dias desde open_until, cancelar
        from datetime import timedelta
        deadline = club.open_until + timedelta(days=3)
        if now >= deadline:
            club.cancel(reason="Creador no respondio en 3 dias")
        # Si no han pasado 3 dias, no hacer nada todavia
    else:
        # Alcanzo el minimo: arrancar (esto ya se maneja en join_view,
        # pero por si acaso)
        club.transition_to(ClubStatus.READING)
```

## Configurar tarea periodica
Opcion 1: via settings
```python
# config/settings.py
CELERY_BEAT_SCHEDULE = {
    "check-club-transitions": {
        "task": "apps.clubs.tasks.check_club_transitions",
        "schedule": 300.0,  # cada 5 minutos
    },
}
```

Opcion 2: via admin de django-celery-beat
Crear un PeriodicTask en /admin/ que ejecute check_club_transitions cada 5 min.

## Otras tareas futuras
- Notificaciones por email (cuando cambia de fase, cuando vence plazo)
- Limpieza de datos de debate despues de CLOSED
- Estadisticas periodicas

## Testing de tareas
```python
from django.test import TestCase
from apps.clubs.tasks import check_club_transitions

class TestTransitions(TestCase):
    def test_reading_to_submission(self):
        # Crear club en READING con submission_starts_at en el pasado
        club = create_test_club(status="READING", submission_starts_at=past)
        check_club_transitions()
        club.refresh_from_db()
        self.assertEqual(club.status, "SUBMISSION")
```
