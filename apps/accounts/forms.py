from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    display_name = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre publico",
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "display_name", "email", "password1", "password2")


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "bio", "email")
