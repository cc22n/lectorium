from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Usuario personalizado de Lectorium.
    Extiende AbstractUser para poder agregar campos en el futuro.
    """

    display_name = models.CharField(
        "nombre público",
        max_length=100,
        blank=True,
    )
    bio = models.TextField(
        "biografía",
        blank=True,
        default="",
    )
    avatar = models.ImageField(
        "avatar",
        upload_to="avatars/",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.display_name or self.username

    @property
    def active_memberships_count(self):
        """Clubes activos donde participa (creados + unidos)."""
        return self.memberships.filter(
            is_active=True,
            club__status__in=["OPEN", "READING", "SUBMISSION", "REVIEW", "DISCUSSION"],
        ).count()

    @property
    def created_clubs_count(self):
        """Clubes activos que ha creado."""
        return self.memberships.filter(
            is_active=True,
            role="CREATOR",
            club__status__in=["OPEN", "READING", "SUBMISSION", "REVIEW", "DISCUSSION"],
        ).count()

    def can_create_club(self):
        """Verifica si puede crear un club nuevo (máx 2 creados, máx 3 activos)."""
        from django.conf import settings
        return (
            self.created_clubs_count < settings.MAX_CLUBS_CREATED
            and self.active_memberships_count < settings.MAX_CLUBS_ACTIVE
        )

    def can_join_club(self):
        """Verifica si puede unirse a un club (máx 3 activos)."""
        from django.conf import settings
        return self.active_memberships_count < settings.MAX_CLUBS_ACTIVE
