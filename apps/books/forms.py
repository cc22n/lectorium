from django import forms
from .models import Book


class ManualBookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ("title", "author", "isbn")
