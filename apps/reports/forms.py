from django import forms

from .models import Report, Comment, DiscussionTopic, VerificationAnswer, ContentFlag

_input_cls = (
    "w-full border border-subtle rounded-lg p-3 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-accent/30 bg-white"
)


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": _input_cls,
                "rows": 12,
                "placeholder": "Escribe tu reflexion sobre el libro...",
            })
        }
        labels = {"text": "Tu reflexion"}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": _input_cls,
                "rows": 3,
                "placeholder": "Escribe un comentario...",
            })
        }
        labels = {"text": "Comentario"}


class DiscussionTopicForm(forms.ModelForm):
    class Meta:
        model = DiscussionTopic
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": _input_cls,
                "rows": 2,
                "placeholder": "Propone un tema para el debate...",
            })
        }
        labels = {"text": "Tema propuesto"}


class VerificationForm(forms.Form):
    """
    Formulario dinamico para el modo MODERATE.
    Genera un campo por cada pregunta definida por el creador.
    """

    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i, question in enumerate(questions or []):
            self.fields[f"q_{i}"] = forms.CharField(
                label=question,
                widget=forms.Textarea(attrs={
                    "class": _input_cls,
                    "rows": 3,
                }),
                max_length=2000,
            )

    def get_answers(self):
        """Devuelve dict listo para guardar en VerificationAnswer.answers."""
        return {
            str(i): self.cleaned_data[f"q_{i}"]
            for i in range(len(self.fields))
        }


class ContentFlagForm(forms.ModelForm):
    class Meta:
        model = ContentFlag
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(attrs={
                "class": _input_cls,
                "rows": 3,
                "placeholder": "Describe brevemente por que reportas este contenido...",
            })
        }
        labels = {"reason": "Motivo del reporte"}
