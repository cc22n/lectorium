from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from datetime import timedelta


class ClubStatus(models.TextChoices):
    OPEN = "OPEN", "Abierto"
    READING = "READING", "En lectura"
    SUBMISSION = "SUBMISSION", "Entrega de reportes"
    REVIEW = "REVIEW", "Revisión de reportes"
    DISCUSSION = "DISCUSSION", "Debate"
    CLOSED = "CLOSED", "Cerrado"
    CANCELLED = "CANCELLED", "Cancelado"


class ClubMode(models.TextChoices):
    STRICT = "STRICT", "Estricto — Reporte obligatorio"
    MODERATE = "MODERATE", "Moderado — Preguntas del creador"
    RELAXED = "RELAXED", "Relajado — Confirmación simple"
    FREE = "FREE", "Libre — Sin requisitos"


class MemberRole(models.TextChoices):
    CREATOR = "CREATOR", "Creador"
    MEMBER = "MEMBER", "Miembro"


class Club(models.Model):
    """
    Club de lectura con ciclo de vida completo.
    Las transiciones de fase son automáticas por fechas (Celery).
    """

    # --- Info básica ---
    name = models.CharField("nombre", max_length=200)
    description = models.TextField(
        "descripción",
        help_text="Incluye reglas, expectativas y detalles del club.",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="clubs",
        verbose_name="libro",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clubs_created",
        verbose_name="creador",
    )

    # --- Configuración ---
    language = models.CharField(
        "idioma",
        max_length=10,
        default="es",
        help_text="Código de idioma (es, en, fr, etc.)",
    )
    mode = models.CharField(
        "modo",
        max_length=10,
        choices=ClubMode.choices,
        default=ClubMode.FREE,
    )
    status = models.CharField(
        "estado",
        max_length=12,
        choices=ClubStatus.choices,
        default=ClubStatus.OPEN,
        db_index=True,
    )

    # --- Límites de miembros ---
    min_members = models.PositiveIntegerField(
        "mínimo de miembros",
        validators=[MinValueValidator(5)],
        help_text="Mínimo 5 (límite de plataforma).",
    )
    max_members = models.PositiveIntegerField(
        "máximo de miembros",
        validators=[MinValueValidator(5), MaxValueValidator(25)],
    )

    # --- Duraciones en días (definidas por el creador) ---
    reading_duration_days = models.PositiveIntegerField(
        "días de lectura",
        validators=[MinValueValidator(7)],
    )
    submission_duration_days = models.PositiveIntegerField(
        "días de entrega",
        validators=[MinValueValidator(3)],
    )
    review_duration_days = models.PositiveIntegerField(
        "días de revisión",
        validators=[MinValueValidator(2)],
    )
    discussion_duration_days = models.PositiveIntegerField(
        "días de debate",
        validators=[MinValueValidator(3)],
    )

    # --- Fechas (calculadas automáticamente al cambiar de fase) ---
    open_until = models.DateTimeField(
        "abierto hasta",
        help_text="Fecha límite para unirse.",
    )
    reading_starts_at = models.DateTimeField("inicio lectura", null=True, blank=True)
    submission_starts_at = models.DateTimeField("inicio entrega", null=True, blank=True)
    review_starts_at = models.DateTimeField("inicio revisión", null=True, blank=True)
    discussion_starts_at = models.DateTimeField("inicio debate", null=True, blank=True)
    closes_at = models.DateTimeField("fecha de cierre", null=True, blank=True)

    # --- Modo moderado: preguntas de verificación ---
    verification_questions = models.JSONField(
        "preguntas de verificación",
        null=True,
        blank=True,
        help_text='Lista de preguntas. Ej: ["¿Quién es el protagonista?", "¿Dónde ocurre?"]',
    )

    # --- Timestamps ---
    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "club"
        verbose_name_plural = "clubes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    # ==============================================================
    # PROPIEDADES
    # ==============================================================

    @property
    def active_members_count(self):
        """Miembros activos en el club."""
        return self.memberships.filter(is_active=True).count()

    @property
    def has_reached_minimum(self):
        """¿Alcanzó el mínimo definido por el creador?"""
        return self.active_members_count >= self.min_members

    @property
    def has_reached_platform_minimum(self):
        """¿Alcanzó el mínimo de la plataforma (5)?"""
        return self.active_members_count >= settings.PLATFORM_MIN_MEMBERS

    @property
    def is_full(self):
        """¿Alcanzó el máximo de miembros?"""
        return self.active_members_count >= self.max_members

    @property
    def current_phase_end(self):
        """Fecha de fin de la fase actual."""
        phase_map = {
            ClubStatus.OPEN: self.open_until,
            ClubStatus.READING: self.submission_starts_at,
            ClubStatus.SUBMISSION: self.review_starts_at,
            ClubStatus.REVIEW: self.discussion_starts_at,
            ClubStatus.DISCUSSION: self.closes_at,
        }
        return phase_map.get(self.status)

    # ==============================================================
    # TRANSICIONES DE FASE
    # ==============================================================

    def calculate_phase_dates(self, start_from=None):
        """
        Calcula todas las fechas de fase a partir de un momento dado.
        Se llama cuando el club pasa de OPEN a READING.
        """
        start = start_from or timezone.now()

        self.reading_starts_at = start
        self.submission_starts_at = start + timedelta(days=self.reading_duration_days)
        self.review_starts_at = self.submission_starts_at + timedelta(days=self.submission_duration_days)
        self.discussion_starts_at = self.review_starts_at + timedelta(days=self.review_duration_days)
        self.closes_at = self.discussion_starts_at + timedelta(days=self.discussion_duration_days)

    def transition_to(self, new_status):
        """
        Transiciona el club a un nuevo estado.
        Valida que la transición sea válida.
        """
        valid_transitions = {
            ClubStatus.OPEN: [ClubStatus.READING, ClubStatus.CANCELLED],
            ClubStatus.READING: [ClubStatus.SUBMISSION, ClubStatus.CANCELLED],
            ClubStatus.SUBMISSION: [ClubStatus.REVIEW, ClubStatus.CANCELLED],
            ClubStatus.REVIEW: [ClubStatus.DISCUSSION, ClubStatus.CANCELLED],
            ClubStatus.DISCUSSION: [ClubStatus.CLOSED, ClubStatus.CANCELLED],
        }

        allowed = valid_transitions.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Transición inválida: {self.status} → {new_status}. "
                f"Transiciones permitidas: {allowed}"
            )

        # Si pasamos de OPEN a READING, calculamos todas las fechas
        if self.status == ClubStatus.OPEN and new_status == ClubStatus.READING:
            self.calculate_phase_dates()

        self.status = new_status
        self.save(update_fields=["status", "updated_at"] + self._phase_date_fields())

    def cancel(self, reason=""):
        """Cancela el club."""
        self.status = ClubStatus.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def _phase_date_fields(self):
        """Campos de fecha que pueden haber cambiado."""
        return [
            "reading_starts_at",
            "submission_starts_at",
            "review_starts_at",
            "discussion_starts_at",
            "closes_at",
        ]

    # ==============================================================
    # VERIFICACIONES DE MIEMBROS
    # ==============================================================

    def can_accept_members(self):
        """¿Puede aceptar nuevos miembros?"""
        return (
            self.status == ClubStatus.OPEN
            and not self.is_full
            and timezone.now() < self.open_until
        )

    def should_cancel_for_low_members(self):
        """¿Debería cancelarse por pocos miembros?"""
        return (
            self.status not in [ClubStatus.OPEN, ClubStatus.CLOSED, ClubStatus.CANCELLED]
            and self.active_members_count <= settings.MIN_MEMBERS_CANCEL_THRESHOLD
        )


class Membership(models.Model):
    """
    Relación entre usuario y club.
    Controla roles y estado de participación.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="usuario",
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="club",
    )
    role = models.CharField(
        "rol",
        max_length=10,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER,
    )
    joined_at = models.DateTimeField("fecha de ingreso", auto_now_add=True)
    is_active = models.BooleanField(
        "activo",
        default=True,
        help_text="False si el usuario abandonó el club.",
    )

    class Meta:
        verbose_name = "membresía"
        verbose_name_plural = "membresías"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "club"],
                name="unique_membership",
            ),
        ]

    def __str__(self):
        status = "activo" if self.is_active else "inactivo"
        return f"{self.user} en {self.club.name} ({status})"

    def leave(self):
        """
        El usuario abandona el club.
        Si estamos en OPEN, se libera el espacio.
        Después de OPEN, solo se marca como inactivo.
        """
        self.is_active = False
        self.save(update_fields=["is_active"])

        # Verificar si el club debe cancelarse por pocos miembros
        if self.club.should_cancel_for_low_members():
            self.club.cancel(reason="Miembros activos por debajo del umbral mínimo")
