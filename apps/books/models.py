from django.conf import settings
from django.db import models


class Book(models.Model):
    """
    Libro registrado en la plataforma.
    Puede venir de Google Books API o ser registro manual.
    """

    title = models.CharField("título", max_length=500)
    author = models.CharField(
        "autor",
        max_length=500,
        help_text="Texto libre. En v2 será entidad separada con relación M:N.",
    )
    isbn = models.CharField("ISBN", max_length=20, blank=True, default="")
    cover_image_url = models.URLField("portada URL", blank=True, default="")
    google_books_id = models.CharField(
        "Google Books ID",
        max_length=50,
        blank=True,
        null=True,
        unique=True,
    )
    is_manual_entry = models.BooleanField(
        "registro manual",
        default=False,
        help_text="True si el usuario lo registró manualmente (no está en Google Books).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books_created",
        verbose_name="registrado por",
    )
    created_at = models.DateTimeField("fecha de registro", auto_now_add=True)

    class Meta:
        verbose_name = "libro"
        verbose_name_plural = "libros"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} — {self.author}"
