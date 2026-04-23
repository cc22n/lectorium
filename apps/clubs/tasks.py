from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

# Filtro reutilizable para contar solo miembros activos
_ACTIVE_MEMBER_FILTER = Q(memberships__is_active=True)


@shared_task
def check_club_transitions():
    """
    Tarea periodica para transicionar automaticamente los clubes segun fechas.
    Corre cada 5 minutos via Celery Beat.
    """
    from apps.clubs.models import Club, ClubStatus

    now = timezone.now()
    creator_decision_days = getattr(settings, "CREATOR_DECISION_DAYS", 3)
    cancel_threshold = settings.MIN_MEMBERS_CANCEL_THRESHOLD
    min_platform = settings.PLATFORM_MIN_MEMBERS

    # 1. Cancelar clubes con pocos miembros activos (umbral <= 3, fases post-OPEN)
    # Anotar conteo de miembros activos en una sola query para evitar N+1.
    active_statuses = [
        ClubStatus.READING,
        ClubStatus.SUBMISSION,
        ClubStatus.REVIEW,
        ClubStatus.DISCUSSION,
    ]
    for club in (
        Club.objects
        .filter(status__in=active_statuses)
        .annotate(member_count=Count("memberships", filter=_ACTIVE_MEMBER_FILTER))
    ):
        if club.member_count <= cancel_threshold:
            club.cancel(reason="Miembros activos por debajo del umbral minimo")

    # 2. Clubes OPEN con fecha vencida — anotar conteo para evitar N+1
    for club in (
        Club.objects
        .filter(status=ClubStatus.OPEN, open_until__lte=now)
        .annotate(member_count=Count("memberships", filter=_ACTIVE_MEMBER_FILTER))
    ):
        count = club.member_count

        if count < min_platform:
            # Menos de 5 miembros: cancelar
            club.cancel(reason="No alcanzo el minimo de la plataforma (5 miembros)")
        elif count >= club.min_members:
            # Alcanzo el minimo del creador: iniciar
            club.transition_to(ClubStatus.READING)
        else:
            # Entre 5 y min_members-1: ventana de decision del creador
            decision_deadline = club.open_until + timedelta(days=creator_decision_days)
            if now >= decision_deadline:
                club.cancel(reason="Plazo de decision del creador vencido")

    # 3. READING -> SUBMISSION
    for club in Club.objects.filter(
        status=ClubStatus.READING,
        submission_starts_at__lte=now,
    ):
        club.transition_to(ClubStatus.SUBMISSION)

    # 4. SUBMISSION -> REVIEW
    for club in Club.objects.filter(
        status=ClubStatus.SUBMISSION,
        review_starts_at__lte=now,
    ):
        club.transition_to(ClubStatus.REVIEW)

    # 5. REVIEW -> DISCUSSION
    for club in Club.objects.filter(
        status=ClubStatus.REVIEW,
        discussion_starts_at__lte=now,
    ):
        club.transition_to(ClubStatus.DISCUSSION)

    # 6. DISCUSSION -> CLOSED
    for club in Club.objects.filter(
        status=ClubStatus.DISCUSSION,
        closes_at__lte=now,
    ):
        club.transition_to(ClubStatus.CLOSED)
