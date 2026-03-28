from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from django.db.models import Q

from apps.clubs.models import Club, ClubStatus, ClubMode, Membership, MemberRole
from .forms import ReportForm, CommentForm, DiscussionTopicForm, VerificationForm, ContentFlagForm
from .models import (
    Report, Reaction, ReactionType, DiscussionTopic, VerificationAnswer,
    ContentFlag, FlagContentType, Comment,
)
from .utils import user_can_discuss


def _get_membership(user, club):
    """Retorna la membresia activa del usuario en el club, o None."""
    return Membership.objects.filter(user=user, club=club, is_active=True).first()


@login_required
def submit_report_view(request, club_pk):
    """Entregar reporte en fase SUBMISSION (o tardio en REVIEW/DISCUSSION)."""
    club = get_object_or_404(Club, pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=club_pk)

    allowed_statuses = [ClubStatus.SUBMISSION, ClubStatus.REVIEW, ClubStatus.DISCUSSION]
    if club.status not in allowed_statuses:
        messages.error(request, "No es posible entregar reportes en esta fase.")
        return redirect("clubs:detail", pk=club_pk)

    existing = Report.objects.filter(user=request.user, club=club).first()
    if existing:
        messages.info(request, "Ya entregaste tu reporte para este club.")
        return redirect("reports:detail", report_pk=existing.pk)

    is_late = club.status != ClubStatus.SUBMISSION

    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.club = club
            report.is_late = is_late
            report.save()
            messages.success(request, "Tu reporte ha sido entregado exitosamente.")
            return redirect("reports:list", club_pk=club_pk)
    else:
        form = ReportForm()

    return render(request, "reports/submit.html", {
        "club": club,
        "form": form,
        "is_late": is_late,
    })


@login_required
def report_list_view(request, club_pk):
    """Lista de reportes del club (visible en REVIEW+)."""
    club = get_object_or_404(Club, pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=club_pk)

    visible_statuses = [ClubStatus.REVIEW, ClubStatus.DISCUSSION, ClubStatus.CLOSED]
    if club.status not in visible_statuses:
        messages.error(request, "Los reportes aun no estan disponibles.")
        return redirect("clubs:detail", pk=club_pk)

    # En CLOSED solo el reporte propio
    if club.status == ClubStatus.CLOSED:
        reports = Report.objects.filter(club=club, user=request.user).select_related("user")
    else:
        reports = Report.objects.filter(club=club).select_related("user")

    # Reacciones del usuario para mostrar estado activo
    user_reactions = set()
    if club.status in [ClubStatus.REVIEW, ClubStatus.DISCUSSION]:
        user_reactions = set(
            Reaction.objects.filter(report__club=club, user=request.user)
            .values_list("report_id", "type")
        )

    my_report = Report.objects.filter(club=club, user=request.user).first()

    return render(request, "reports/list.html", {
        "club": club,
        "reports": reports,
        "user_reactions": user_reactions,
        "my_report": my_report,
        "reaction_types": ReactionType.choices,
        "can_react": club.status in [ClubStatus.REVIEW, ClubStatus.DISCUSSION],
    })


@login_required
def report_detail_view(request, report_pk):
    """Detalle de un reporte con reacciones y comentarios."""
    report = get_object_or_404(
        Report.objects.select_related("user", "club", "club__book"),
        pk=report_pk,
    )
    club = report.club
    membership = _get_membership(request.user, club)

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=club.pk)

    visible_statuses = [ClubStatus.REVIEW, ClubStatus.DISCUSSION, ClubStatus.CLOSED]
    if club.status not in visible_statuses:
        messages.error(request, "Los reportes aun no estan disponibles.")
        return redirect("clubs:detail", pk=club.pk)

    # En CLOSED solo el autor puede ver su propio reporte
    if club.status == ClubStatus.CLOSED and report.user != request.user:
        messages.error(request, "Solo puedes ver tu propio reporte en un club cerrado.")
        return redirect("clubs:detail", pk=club.pk)

    can_react = club.status in [ClubStatus.REVIEW, ClubStatus.DISCUSSION]
    can_comment = club.status == ClubStatus.DISCUSSION
    can_propose_topic = club.status in [ClubStatus.REVIEW, ClubStatus.DISCUSSION]

    user_reactions = set(
        Reaction.objects.filter(report=report, user=request.user).values_list("type", flat=True)
    )

    # Contar reacciones por tipo
    reaction_counts = {}
    for rt, _ in ReactionType.choices:
        reaction_counts[rt] = Reaction.objects.filter(report=report, type=rt).count()

    comments = report.comments.select_related("user").all()
    topics = club.discussion_topics.select_related("user").all()

    comment_form = CommentForm() if can_comment else None
    topic_form = DiscussionTopicForm() if can_propose_topic else None

    return render(request, "reports/detail.html", {
        "report": report,
        "club": club,
        "user_reactions": user_reactions,
        "reaction_types": ReactionType.choices,
        "reaction_counts": reaction_counts,
        "comments": comments,
        "comment_form": comment_form,
        "topics": topics,
        "topic_form": topic_form,
        "can_react": can_react,
        "can_comment": can_comment,
        "can_propose_topic": can_propose_topic,
        "is_own_report": report.user == request.user,
    })


@login_required
@require_POST
def toggle_reaction_view(request, report_pk):
    """Toggle de reaccion en un reporte (HTMX POST)."""
    report = get_object_or_404(Report.objects.select_related("club"), pk=report_pk)
    club = report.club
    membership = _get_membership(request.user, club)

    if not membership:
        return HttpResponse(status=403)

    if club.status not in [ClubStatus.REVIEW, ClubStatus.DISCUSSION]:
        return HttpResponse(status=403)

    reaction_type = request.POST.get("type")
    if reaction_type not in dict(ReactionType.choices):
        return HttpResponse(status=400)

    existing = Reaction.objects.filter(
        user=request.user, report=report, type=reaction_type
    ).first()

    if existing:
        existing.delete()
        active = False
    else:
        Reaction.objects.create(user=request.user, report=report, type=reaction_type)
        active = True

    count = Reaction.objects.filter(report=report, type=reaction_type).count()

    return render(request, "reports/includes/reaction_button.html", {
        "report": report,
        "reaction_type": reaction_type,
        "reaction_label": dict(ReactionType.choices)[reaction_type],
        "count": count,
        "active": active,
    })


@login_required
@require_POST
def add_comment_view(request, report_pk):
    """Agregar comentario a un reporte (HTMX POST)."""
    report = get_object_or_404(Report.objects.select_related("club"), pk=report_pk)
    club = report.club
    membership = _get_membership(request.user, club)

    if not membership:
        return HttpResponse(status=403)

    if club.status != ClubStatus.DISCUSSION:
        return HttpResponse(status=403)

    can_discuss, _ = user_can_discuss(request.user, club)
    if not can_discuss:
        return HttpResponse(status=403)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.report = report
        comment.user = request.user
        comment.save()

        if request.htmx:
            return render(request, "reports/includes/comment.html", {"comment": comment})

    return redirect("reports:detail", report_pk=report_pk)


@login_required
@require_POST
def propose_topic_view(request, club_pk):
    """Proponer tema de debate (HTMX POST)."""
    club = get_object_or_404(Club, pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership:
        return HttpResponse(status=403)

    if club.status not in [ClubStatus.REVIEW, ClubStatus.DISCUSSION]:
        return HttpResponse(status=403)

    form = DiscussionTopicForm(request.POST)
    if form.is_valid():
        topic = form.save(commit=False)
        topic.club = club
        topic.user = request.user
        topic.save()

        if request.htmx:
            topics = club.discussion_topics.select_related("user").all()
            return render(request, "reports/includes/topics_list.html", {
                "topics": topics,
                "club": club,
            })

    return redirect("clubs:detail", pk=club_pk)


@login_required
def discussion_view(request, club_pk):
    """Pagina de debate en tiempo real con WebSockets."""
    club = get_object_or_404(Club.objects.select_related("book"), pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=club_pk)

    if club.status != ClubStatus.DISCUSSION:
        messages.error(request, "El debate no esta activo en este momento.")
        return redirect("clubs:detail", pk=club_pk)

    can_discuss, _ = user_can_discuss(request.user, club)
    if not can_discuss:
        messages.warning(request, "Necesitas verificar tu lectura antes de acceder al debate.")
        return redirect("reports:verify", club_pk=club_pk)

    topics = club.discussion_topics.select_related("user").all()
    is_creator = membership.role == MemberRole.CREATOR

    return render(request, "reports/discussion.html", {
        "club": club,
        "topics": topics,
        "is_creator": is_creator,
    })


# ==============================================================
# VERIFICACION DE LECTURA — FASE 4
# ==============================================================

@login_required
def verify_view(request, club_pk):
    """
    Muestra el formulario de verificacion segun el modo del club.
    - FREE: redirige directo al debate
    - STRICT: informa que necesita reporte, redirige a entregarlo
    - RELAXED: boton de confirmacion unico
    - MODERATE: formulario con preguntas del creador
    """
    club = get_object_or_404(Club.objects.select_related("book"), pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=club_pk)

    allowed_statuses = [ClubStatus.REVIEW, ClubStatus.DISCUSSION]
    if club.status not in allowed_statuses:
        return redirect("clubs:detail", pk=club_pk)

    # FREE: no necesita verificacion
    if club.mode == ClubMode.FREE:
        return redirect("reports:discussion", club_pk=club_pk)

    # STRICT: necesita reporte
    if club.mode == ClubMode.STRICT:
        has_report = Report.objects.filter(user=request.user, club=club).exists()
        if has_report:
            return redirect("reports:discussion", club_pk=club_pk)
        messages.info(request, "En este club debes entregar tu reporte para acceder al debate.")
        return redirect("reports:submit", club_pk=club_pk)

    # RELAXED o MODERATE: verificar si ya existe respuesta
    existing = VerificationAnswer.objects.filter(user=request.user, club=club).first()

    if club.mode == ClubMode.RELAXED:
        if existing:
            if club.status == ClubStatus.DISCUSSION:
                return redirect("reports:discussion", club_pk=club_pk)
            messages.success(request, "Ya confirmaste tu lectura.")
            return redirect("clubs:detail", pk=club_pk)

        if request.method == "POST":
            VerificationAnswer.objects.create(
                user=request.user,
                club=club,
                answers={"confirmed": True},
                passed=True,  # RELAXED es auto-aprobado
            )
            messages.success(request, "Lectura confirmada. Ya puedes acceder al debate cuando abra.")
            if club.status == ClubStatus.DISCUSSION:
                return redirect("reports:discussion", club_pk=club_pk)
            return redirect("clubs:detail", pk=club_pk)

        return render(request, "reports/verify.html", {
            "club": club,
            "mode": "relaxed",
        })

    # MODERATE
    if existing:
        return render(request, "reports/verify.html", {
            "club": club,
            "mode": "moderate_pending",
            "verification": existing,
        })

    questions = club.verification_questions or []
    if not questions:
        # El creador no definio preguntas, tratar como FREE
        VerificationAnswer.objects.create(
            user=request.user,
            club=club,
            answers={},
            passed=True,
        )
        return redirect("clubs:detail", pk=club_pk)

    if request.method == "POST":
        form = VerificationForm(questions, request.POST)
        if form.is_valid():
            VerificationAnswer.objects.create(
                user=request.user,
                club=club,
                answers=form.get_answers(),
                passed=False,
            )
            messages.success(request, "Respuestas enviadas. El creador las revisara pronto.")
            return redirect("clubs:detail", pk=club_pk)
    else:
        form = VerificationForm(questions)

    return render(request, "reports/verify.html", {
        "club": club,
        "mode": "moderate_form",
        "form": form,
        "questions": questions,
    })


@login_required
def verification_review_view(request, club_pk):
    """Vista del creador para revisar respuestas pendientes (modo MODERATE)."""
    club = get_object_or_404(Club.objects.select_related("book"), pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership or membership.role != MemberRole.CREATOR:
        messages.error(request, "Solo el creador puede revisar verificaciones.")
        return redirect("clubs:detail", pk=club_pk)

    if club.mode != ClubMode.MODERATE:
        return redirect("clubs:detail", pk=club_pk)

    pending = VerificationAnswer.objects.filter(
        club=club, passed=False
    ).select_related("user")
    approved = VerificationAnswer.objects.filter(
        club=club, passed=True
    ).select_related("user")

    questions = club.verification_questions or []

    return render(request, "reports/verification_review.html", {
        "club": club,
        "pending": pending,
        "approved": approved,
        "questions": questions,
    })


@login_required
@require_POST
def approve_verification_view(request, club_pk, answer_pk):
    """El creador aprueba una respuesta de verificacion."""
    club = get_object_or_404(Club, pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership or membership.role != MemberRole.CREATOR:
        return HttpResponse(status=403)

    answer = get_object_or_404(VerificationAnswer, pk=answer_pk, club=club)
    answer.passed = True
    answer.save(update_fields=["passed"])

    messages.success(request, f"Verificacion de {answer.user} aprobada.")
    return redirect("reports:verification_review", club_pk=club_pk)


@login_required
@require_POST
def reject_verification_view(request, club_pk, answer_pk):
    """El creador rechaza una respuesta (la elimina para que el usuario pueda reintentar)."""
    club = get_object_or_404(Club, pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership or membership.role != MemberRole.CREATOR:
        return HttpResponse(status=403)

    answer = get_object_or_404(VerificationAnswer, pk=answer_pk, club=club)
    user_name = str(answer.user)
    answer.delete()

    messages.success(request, f"Respuestas de {user_name} rechazadas. El usuario podra reintentar.")
    return redirect("reports:verification_review", club_pk=club_pk)


# ==============================================================
# MODERACION Y FLAGS — FASE 5
# ==============================================================

def _verify_content_in_club(content_type, content_id, club):
    """Verifica que el contenido referenciado pertenezca al club dado."""
    if content_type == FlagContentType.REPORT:
        return Report.objects.filter(pk=content_id, club=club).exists()
    if content_type == FlagContentType.COMMENT:
        return Comment.objects.filter(pk=content_id, report__club=club).exists()
    if content_type == FlagContentType.DISCUSSION_TOPIC:
        return DiscussionTopic.objects.filter(pk=content_id, club=club).exists()
    return False


def _resolve_content_object(flag):
    """Devuelve el objeto concreto referenciado por un ContentFlag."""
    if flag.content_type == FlagContentType.REPORT:
        return Report.objects.filter(pk=flag.content_id).select_related("user").first()
    if flag.content_type == FlagContentType.COMMENT:
        return Comment.objects.filter(pk=flag.content_id).select_related("user", "report").first()
    if flag.content_type == FlagContentType.DISCUSSION_TOPIC:
        return DiscussionTopic.objects.filter(pk=flag.content_id).select_related("user").first()
    return None


@login_required
def flag_content_view(request, club_pk):
    """
    Cualquier miembro puede reportar contenido inapropiado.
    GET: muestra formulario con razon.
    POST: crea el flag.
    Recibe content_type y content_id como parametros de URL o campos hidden.
    """
    club = get_object_or_404(Club.objects.select_related("book"), pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership:
        messages.error(request, "No eres miembro de este club.")
        return redirect("clubs:detail", pk=club_pk)

    content_type = request.GET.get("type") or request.POST.get("content_type", "")
    content_id_str = request.GET.get("id") or request.POST.get("content_id", "")

    if content_type not in dict(FlagContentType.choices) or not content_id_str.isdigit():
        messages.error(request, "Contenido no valido.")
        return redirect("clubs:detail", pk=club_pk)

    content_id = int(content_id_str)

    if not _verify_content_in_club(content_type, content_id, club):
        messages.error(request, "El contenido no pertenece a este club.")
        return redirect("clubs:detail", pk=club_pk)

    # Evitar duplicados del mismo usuario
    already_flagged = ContentFlag.objects.filter(
        reported_by=request.user,
        content_type=content_type,
        content_id=content_id,
        resolved=False,
    ).exists()
    if already_flagged:
        messages.info(request, "Ya reportaste este contenido anteriormente.")
        return redirect("clubs:detail", pk=club_pk)

    if request.method == "POST":
        form = ContentFlagForm(request.POST)
        if form.is_valid():
            flag = form.save(commit=False)
            flag.reported_by = request.user
            flag.content_type = content_type
            flag.content_id = content_id
            flag.save()
            messages.success(request, "Contenido reportado. El moderador lo revisara pronto.")
            return redirect("clubs:detail", pk=club_pk)
    else:
        form = ContentFlagForm()

    # Obtener preview del contenido (lookup manual sin un ContentFlag guardado)
    class _FakeFlag:
        pass
    fake = _FakeFlag()
    fake.content_type = content_type
    fake.content_id = content_id
    content_obj = _resolve_content_object(fake)

    return render(request, "reports/flag_form.html", {
        "club": club,
        "form": form,
        "content_type": content_type,
        "content_id": content_id,
        "content_type_label": dict(FlagContentType.choices).get(content_type, ""),
        "content_obj": content_obj,
    })


@login_required
def moderation_view(request, club_pk):
    """Vista del creador para gestionar flags pendientes del club."""
    club = get_object_or_404(Club.objects.select_related("book"), pk=club_pk)
    membership = _get_membership(request.user, club)

    if not membership or membership.role != MemberRole.CREATOR:
        messages.error(request, "Solo el creador puede acceder a la moderacion.")
        return redirect("clubs:detail", pk=club_pk)

    # Obtener IDs de todo el contenido del club
    report_ids = list(Report.objects.filter(club=club).values_list("id", flat=True))
    comment_ids = list(Comment.objects.filter(report__club=club).values_list("id", flat=True))
    topic_ids = list(DiscussionTopic.objects.filter(club=club).values_list("id", flat=True))

    pending_flags = ContentFlag.objects.filter(
        Q(content_type=FlagContentType.REPORT, content_id__in=report_ids)
        | Q(content_type=FlagContentType.COMMENT, content_id__in=comment_ids)
        | Q(content_type=FlagContentType.DISCUSSION_TOPIC, content_id__in=topic_ids),
        resolved=False,
    ).select_related("reported_by").order_by("-created_at")

    resolved_flags = ContentFlag.objects.filter(
        Q(content_type=FlagContentType.REPORT, content_id__in=report_ids)
        | Q(content_type=FlagContentType.COMMENT, content_id__in=comment_ids)
        | Q(content_type=FlagContentType.DISCUSSION_TOPIC, content_id__in=topic_ids),
        resolved=True,
    ).select_related("reported_by").order_by("-created_at")[:20]

    # Anotar cada flag con su objeto de contenido
    def annotate(flags):
        result = []
        for f in flags:
            result.append((f, _resolve_content_object(f)))
        return result

    return render(request, "reports/moderation.html", {
        "club": club,
        "pending_flags": annotate(pending_flags),
        "resolved_flags": annotate(resolved_flags),
    })


@login_required
@require_POST
def dismiss_flag_view(request, flag_pk):
    """El creador desestima el flag sin eliminar el contenido."""
    flag = get_object_or_404(ContentFlag, pk=flag_pk, resolved=False)
    club = _get_flag_club(flag)

    if not club:
        return HttpResponse(status=404)

    membership = _get_membership(request.user, club)
    if not membership or membership.role != MemberRole.CREATOR:
        return HttpResponse(status=403)

    flag.resolved = True
    flag.save(update_fields=["resolved"])
    messages.success(request, "Flag desestimado.")
    return redirect("reports:moderation", club_pk=club.pk)


@login_required
@require_POST
def delete_flagged_content_view(request, flag_pk):
    """El creador elimina el contenido reportado y marca el flag como resuelto."""
    flag = get_object_or_404(ContentFlag, pk=flag_pk, resolved=False)
    club = _get_flag_club(flag)

    if not club:
        return HttpResponse(status=404)

    membership = _get_membership(request.user, club)
    if not membership or membership.role != MemberRole.CREATOR:
        return HttpResponse(status=403)

    content = _resolve_content_object(flag)
    if content:
        content.delete()
        messages.success(request, "Contenido eliminado correctamente.")
    else:
        messages.warning(request, "El contenido ya habia sido eliminado.")

    # Marcar todos los flags pendientes de este contenido como resueltos
    ContentFlag.objects.filter(
        content_type=flag.content_type,
        content_id=flag.content_id,
        resolved=False,
    ).update(resolved=True)

    return redirect("reports:moderation", club_pk=club.pk)


def _get_flag_club(flag):
    """Obtiene el club al que pertenece el contenido de un flag."""
    if flag.content_type == FlagContentType.REPORT:
        report = Report.objects.filter(pk=flag.content_id).select_related("club").first()
        return report.club if report else None
    if flag.content_type == FlagContentType.COMMENT:
        comment = Comment.objects.filter(pk=flag.content_id).select_related("report__club").first()
        return comment.report.club if comment else None
    if flag.content_type == FlagContentType.DISCUSSION_TOPIC:
        topic = DiscussionTopic.objects.filter(pk=flag.content_id).select_related("club").first()
        return topic.club if topic else None
    return None
