from datetime import date

from django import forms
from django.conf import settings

from .models import ClubMode


class CreateClubForm(forms.Form):
    """
    Formulario para crear un club.
    No usa ModelForm porque necesitamos manejar book_id
    y verification_questions de forma personalizada.
    """

    book_id = forms.IntegerField(widget=forms.HiddenInput())
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
    language = forms.ChoiceField(
        choices=[("es", "Espanol"), ("en", "English"), ("fr", "Francais"), ("pt", "Portugues")],
        initial="es",
    )
    mode = forms.ChoiceField(choices=ClubMode.choices, initial=ClubMode.FREE)
    min_members = forms.IntegerField(min_value=5, max_value=25, initial=5)
    max_members = forms.IntegerField(min_value=5, max_value=25, initial=20)
    reading_duration_days = forms.IntegerField(min_value=7, initial=30)
    submission_duration_days = forms.IntegerField(min_value=3, initial=7)
    review_duration_days = forms.IntegerField(min_value=2, initial=3)
    discussion_duration_days = forms.IntegerField(min_value=3, initial=7)
    open_until = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    verification_questions = forms.CharField(required=False, widget=forms.Textarea)

    def clean_book_id(self):
        from apps.books.models import Book

        book_id = self.cleaned_data["book_id"]
        try:
            Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            raise forms.ValidationError("Libro no encontrado. Selecciona un libro valido.")
        return book_id

    def clean_open_until(self):
        open_until = self.cleaned_data["open_until"]
        if open_until <= date.today():
            raise forms.ValidationError("La fecha debe ser en el futuro.")
        return open_until

    def clean(self):
        cleaned_data = super().clean()
        min_m = cleaned_data.get("min_members", 5)
        max_m = cleaned_data.get("max_members", 20)

        if min_m > max_m:
            raise forms.ValidationError(
                "El minimo de miembros no puede ser mayor que el maximo."
            )

        if max_m > settings.PLATFORM_MAX_MEMBERS_LIMIT:
            raise forms.ValidationError(
                f"El maximo de miembros no puede superar {settings.PLATFORM_MAX_MEMBERS_LIMIT}."
            )

        return cleaned_data

    def get_verification_questions_json(self):
        """Convierte las preguntas de texto (una por linea) a JSON."""
        raw = self.cleaned_data.get("verification_questions", "").strip()
        if not raw:
            return None
        questions = [q.strip() for q in raw.splitlines() if q.strip()]
        return questions if questions else None
