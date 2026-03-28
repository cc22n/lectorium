from django.conf import settings
from django.db import models


class ReactionType(models.TextChoices):
    LIKE = "LIKE", "Me gusta"
    INTERESTING = "INTERESTING", "Interesante"
    AGREE = "AGREE", "De acuerdo"
    DISAGREE = "DISAGREE", "En desacuerdo"


class FlagContentType(models.TextChoices):
    REPORT = "REPORT", "Reporte"
    COMMENT = "COMMENT", "Comentario"
    DISCUSSION_TOPIC = "DISCUSSION_TOPIC", "Tema de debate"


class Report(models.Model):
    """
    Reflexión/reporte de un usuario sobre el libro de un club.
    Solo uno por usuario por club.
    No visible para otros hasta que cierra la fase SUBMISSION.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="club",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="autor",
    )
    text = models.TextField("reflexión")
    submitted_at = models.DateTimeField("fecha de entrega", auto_now_add=True)
    is_late = models.BooleanField(
        "entrega tardía",
        default=False,
        help_text="True si se entregó fuera del periodo de SUBMISSION.",
    )

    class Meta:
        verbose_name = "reporte"
        verbose_name_plural = "reportes"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "club"],
                name="unique_report_per_user_per_club",
            ),
        ]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Reporte de {self.user} en {self.club.name}"


class Reaction(models.Model):
    """
    Reacción a un reporte (like, interesante, de acuerdo, en desacuerdo).
    Solo disponible a partir de la fase REVIEW.
    """

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="reactions",
        verbose_name="reporte",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reactions",
        verbose_name="usuario",
    )
    type = models.CharField(
        "tipo",
        max_length=15,
        choices=ReactionType.choices,
    )
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "reacción"
        verbose_name_plural = "reacciones"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "report", "type"],
                name="unique_reaction_per_type",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.get_type_display()} en reporte de {self.report.user}"


class Comment(models.Model):
    """
    Comentario en un reporte.
    Solo permitido a partir de la fase DISCUSSION.
    """

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="reporte",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="autor",
    )
    text = models.TextField("comentario")
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "comentario"
        verbose_name_plural = "comentarios"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comentario de {self.user} en reporte de {self.report.user}"


class DiscussionTopic(models.Model):
    """
    Tema propuesto para el debate.
    Disponible en todos los modos. Se propone durante la fase REVIEW.
    Sirve como agenda para que el moderador guíe la discusión.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="discussion_topics",
        verbose_name="club",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_topics",
        verbose_name="propuesto por",
    )
    text = models.TextField("tema propuesto")
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "tema de debate"
        verbose_name_plural = "temas de debate"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Tema: {self.text[:50]}... ({self.club.name})"


class VerificationAnswer(models.Model):
    """
    Respuestas a las preguntas de verificación del modo moderado.
    El creador define las preguntas, el usuario las responde para
    poder participar en el debate.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="verification_answers",
        verbose_name="club",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_answers",
        verbose_name="usuario",
    )
    answers = models.JSONField(
        "respuestas",
        help_text="JSON con las respuestas a cada pregunta.",
    )
    passed = models.BooleanField(
        "aprobado",
        default=False,
        help_text="Si el moderador aprobó las respuestas.",
    )
    submitted_at = models.DateTimeField("fecha de envío", auto_now_add=True)

    class Meta:
        verbose_name = "respuesta de verificación"
        verbose_name_plural = "respuestas de verificación"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "club"],
                name="unique_verification_per_user_per_club",
            ),
        ]

    def __str__(self):
        status = "aprobado" if self.passed else "pendiente"
        return f"Verificación de {self.user} en {self.club.name} ({status})"


class ContentFlag(models.Model):
    """
    Reporte de contenido inapropiado.
    Los miembros pueden marcar reportes, comentarios o temas de debate.
    El moderador (creador) revisa y resuelve.
    """

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="flags_created",
        verbose_name="reportado por",
    )
    content_type = models.CharField(
        "tipo de contenido",
        max_length=20,
        choices=FlagContentType.choices,
    )
    content_id = models.PositiveIntegerField(
        "ID del contenido",
        help_text="ID del reporte, comentario o tema reportado.",
    )
    reason = models.TextField("motivo")
    created_at = models.DateTimeField("fecha", auto_now_add=True)
    resolved = models.BooleanField("resuelto", default=False)

    class Meta:
        verbose_name = "flag de contenido"
        verbose_name_plural = "flags de contenido"
        ordering = ["-created_at"]

    def __str__(self):
        status = "resuelto" if self.resolved else "pendiente"
        return f"Flag en {self.content_type} #{self.content_id} ({status})"
