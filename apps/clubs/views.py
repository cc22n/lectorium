from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.books.models import Book
from apps.reports.models import Report, VerificationAnswer
from apps.reports.utils import user_can_discuss
from .forms import CreateClubForm
from .models import Club, ClubStatus, ClubMode, Membership, MemberRole


def home_view(request):
    """Landing page con clubes abiertos y clubes del usuario."""
    open_clubs = (
        Club.objects.filter(status=ClubStatus.OPEN)
        .select_related("book", "creator")
        .order_by("-created_at")[:6]
    )

    my_clubs = None
    if request.user.is_authenticated:
        my_clubs = (
            request.user.memberships
            .filter(
                is_active=True,
                club__status__in=[
                    ClubStatus.OPEN, ClubStatus.READING,
                    ClubStatus.SUBMISSION, ClubStatus.REVIEW,
                    ClubStatus.DISCUSSION,
                ],
            )
            .select_related("club", "club__book")
        )

    return render(request, "clubs/home.html", {
        "open_clubs": open_clubs,
        "my_clubs": my_clubs,
    })


def explore_view(request):
    """Explorar clubes con filtros."""
    queryset = Club.objects.select_related("book", "creator").order_by("-created_at")

    # Filtro por status.
    # "all" muestra todos los estados. Cualquier otro valor filtra exactamente.
    # Por defecto se muestran solo clubes OPEN.
    status = request.GET.get("status", "OPEN")
    if status != "all":
        queryset = queryset.filter(status=status)

    # Filtro por idioma
    language = request.GET.get("language")
    if language:
        queryset = queryset.filter(language=language)

    # Filtro por modo
    mode = request.GET.get("mode")
    if mode:
        queryset = queryset.filter(mode=mode)

    paginator = Paginator(queryset, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "clubs/explore.html", {
        "clubs": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
    })


def detail_view(request, pk):
    """Detalle de un club."""
    club = get_object_or_404(
        Club.objects.select_related("book", "creator"),
        pk=pk,
    )

    # Materializamos los miembros activos una sola vez; se usan en la vista
    # y en el template para la lista y el conteo.
    members = list(club.memberships.filter(is_active=True).select_related("user"))

    is_member = False
    membership = None
    can_join = False
    my_report = None
    user_verified = False
    user_verification = None
    pending_verifications_count = 0

    if request.user.is_authenticated:
        membership = club.memberships.filter(
            user=request.user, is_active=True
        ).first()
        is_member = membership is not None
        can_join = (
            not is_member
            and club.can_accept_members()
            and request.user.can_join_club()
        )
        if is_member:
            my_report = Report.objects.filter(user=request.user, club=club).first()
            # Verificacion de lectura (relevante en REVIEW y DISCUSSION)
            if club.status in [ClubStatus.REVIEW, ClubStatus.DISCUSSION]:
                user_verified, user_verification = user_can_discuss(request.user, club)
                # Contador de pendientes para el creador en modo MODERATE
                if (
                    membership
                    and membership.role == MemberRole.CREATOR
                    and club.mode == ClubMode.MODERATE
                ):
                    pending_verifications_count = VerificationAnswer.objects.filter(
                        club=club, passed=False
                    ).count()

    return render(request, "clubs/detail.html", {
        "club": club,
        "members": members,
        "members_count": len(members),
        "is_member": is_member,
        "membership": membership,
        "can_join": can_join,
        "my_report": my_report,
        "user_verified": user_verified,
        "user_verification": user_verification,
        "pending_verifications_count": pending_verifications_count,
    })


@login_required
def create_view(request):
    """Crear un club nuevo."""
    can_create = request.user.can_create_club()

    if request.method == "POST":
        if not can_create:
            messages.error(request, "No puedes crear mas clubes.")
            return redirect("clubs:home")

        form = CreateClubForm(request.POST)
        if form.is_valid():
            book = get_object_or_404(Book, pk=form.cleaned_data["book_id"])

            # Convertir date a datetime con timezone
            open_until_date = form.cleaned_data["open_until"]
            open_until_dt = timezone.make_aware(
                datetime.combine(open_until_date, datetime.max.time().replace(microsecond=0))
            )

            club = Club.objects.create(
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                book=book,
                creator=request.user,
                language=form.cleaned_data["language"],
                mode=form.cleaned_data["mode"],
                min_members=form.cleaned_data["min_members"],
                max_members=form.cleaned_data["max_members"],
                reading_duration_days=form.cleaned_data["reading_duration_days"],
                submission_duration_days=form.cleaned_data["submission_duration_days"],
                review_duration_days=form.cleaned_data["review_duration_days"],
                discussion_duration_days=form.cleaned_data["discussion_duration_days"],
                open_until=open_until_dt,
                verification_questions=form.get_verification_questions_json(),
            )

            # Crear membership del creador
            Membership.objects.create(
                user=request.user,
                club=club,
                role=MemberRole.CREATOR,
            )

            messages.success(request, f"Club '{club.name}' creado exitosamente!")
            return redirect("clubs:detail", pk=club.pk)
    else:
        form = CreateClubForm()

    return render(request, "clubs/create.html", {
        "form": form,
        "can_create": can_create,
    })


@login_required
def join_view(request, pk):
    """Unirse a un club."""
    club = get_object_or_404(Club, pk=pk)

    if request.method != "POST":
        return redirect("clubs:detail", pk=pk)

    # Verificar que puede unirse
    if not club.can_accept_members():
        messages.error(request, "Este club no acepta nuevos miembros.")
        return redirect("clubs:detail", pk=pk)

    if not request.user.can_join_club():
        messages.error(request, "Ya alcanzaste el limite de clubes activos (maximo 3).")
        return redirect("clubs:detail", pk=pk)

    # Verificar que no es ya miembro
    existing = Membership.objects.filter(user=request.user, club=club).first()
    if existing:
        if existing.is_active:
            messages.info(request, "Ya eres miembro de este club.")
        else:
            # Re-activar membership si habia abandonado en fase OPEN
            if club.status == ClubStatus.OPEN:
                existing.is_active = True
                existing.save(update_fields=["is_active"])
                messages.success(request, f"Te has unido de nuevo a '{club.name}'.")
            else:
                messages.error(request, "No puedes volver a unirte a este club.")
        return redirect("clubs:detail", pk=pk)

    Membership.objects.create(
        user=request.user,
        club=club,
        role=MemberRole.MEMBER,
    )

    messages.success(request, f"Te has unido a '{club.name}'!")

    # Verificar si se alcanzo el minimo para arrancar automaticamente.
    # Re-leer desde la BD para que active_members_count incluya al nuevo miembro.
    club.refresh_from_db()
    if club.status == ClubStatus.OPEN and club.has_reached_minimum:
        club.transition_to(ClubStatus.READING)
        messages.info(
            request,
            "El club ha alcanzado el minimo de miembros. La fase de lectura ha comenzado!"
        )

    return redirect("clubs:detail", pk=pk)


@login_required
def leave_view(request, pk):
    """Abandonar un club."""
    club = get_object_or_404(Club, pk=pk)

    if request.method != "POST":
        return redirect("clubs:detail", pk=pk)

    membership = Membership.objects.filter(
        user=request.user, club=club, is_active=True
    ).first()

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=pk)

    if membership.role == MemberRole.CREATOR:
        messages.error(request, "El creador no puede abandonar el club.")
        return redirect("clubs:detail", pk=pk)

    membership.leave()
    messages.success(request, f"Has abandonado '{club.name}'.")

    return redirect("clubs:home")


@login_required
def force_start_view(request, pk):
    """
    El creador fuerza el inicio del club cuando tiene 5+ miembros
    pero no alcanzo el minimo definido, dentro de la ventana de decision.
    """
    from datetime import timedelta
    from django.conf import settings as django_settings

    club = get_object_or_404(Club, pk=pk)

    if request.method != "POST":
        return redirect("clubs:detail", pk=pk)

    membership = Membership.objects.filter(
        user=request.user, club=club, is_active=True, role=MemberRole.CREATOR
    ).first()

    if not membership:
        messages.error(request, "Solo el creador puede iniciar el club.")
        return redirect("clubs:detail", pk=pk)

    if club.status != ClubStatus.OPEN:
        messages.error(request, "El club ya no esta en fase de inscripcion.")
        return redirect("clubs:detail", pk=pk)

    if not club.has_reached_platform_minimum:
        messages.error(request, "El club necesita al menos 5 miembros para iniciar.")
        return redirect("clubs:detail", pk=pk)

    now = timezone.now()
    creator_decision_days = getattr(django_settings, "CREATOR_DECISION_DAYS", 3)
    decision_deadline = club.open_until + timedelta(days=creator_decision_days)

    if now < club.open_until:
        messages.error(request, "El periodo de inscripcion aun no ha vencido.")
        return redirect("clubs:detail", pk=pk)

    if now >= decision_deadline:
        messages.error(request, "El plazo para iniciar el club ha vencido.")
        return redirect("clubs:detail", pk=pk)

    club.transition_to(ClubStatus.READING)
    messages.success(request, f"El club '{club.name}' ha iniciado la fase de lectura.")

    return redirect("clubs:detail", pk=pk)


@login_required
def close_discussion_view(request, pk):
    """El creador cierra el debate antes de tiempo."""
    club = get_object_or_404(Club, pk=pk)

    if request.method != "POST":
        return redirect("clubs:detail", pk=pk)

    membership = Membership.objects.filter(
        user=request.user, club=club, is_active=True, role=MemberRole.CREATOR
    ).first()

    if not membership:
        messages.error(request, "Solo el creador puede cerrar el debate.")
        return redirect("clubs:detail", pk=pk)

    if club.status != ClubStatus.DISCUSSION:
        messages.error(request, "El club no esta en fase de debate.")
        return redirect("clubs:detail", pk=pk)

    club.transition_to(ClubStatus.CLOSED)
    messages.success(request, f"El debate de '{club.name}' ha sido cerrado.")

    return redirect("clubs:detail", pk=pk)
