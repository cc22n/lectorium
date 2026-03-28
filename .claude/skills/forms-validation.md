# Skill: Formularios y validacion

## Tipos de formulario en el proyecto

### ModelForm — para CRUD simple
```python
class ManualBookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ("title", "author", "isbn")
```

### Form — para logica compleja
Cuando el formulario no mapea 1:1 al modelo o necesita procesamiento especial.
Ejemplo: CreateClubForm maneja book_id como hidden input y verification_questions como texto plano que se convierte a JSON.

## Patrones de validacion

### Validar campo individual
```python
def clean_open_until(self):
    value = self.cleaned_data["open_until"]
    if value <= date.today():
        raise forms.ValidationError("La fecha debe ser en el futuro.")
    return value
```

### Validar multiples campos juntos
```python
def clean(self):
    cleaned_data = super().clean()
    min_m = cleaned_data.get("min_members", 5)
    max_m = cleaned_data.get("max_members", 20)
    if min_m > max_m:
        raise forms.ValidationError("Min no puede ser mayor que max.")
    return cleaned_data
```

### Validar contra la base de datos
```python
def clean_book_id(self):
    book_id = self.cleaned_data["book_id"]
    try:
        Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        raise forms.ValidationError("Libro no encontrado.")
    return book_id
```

## Renderizado en templates
NO usar {{ form.as_p }} ni {{ form.as_table }}. Siempre renderizar campo por campo para control total del diseno:

```html
<div>
  <label for="id_name" class="block text-sm font-medium text-ink mb-1.5">Nombre</label>
  <input type="text" name="name" id="id_name"
         value="{{ form.name.value|default:'' }}"
         class="w-full border border-subtle rounded-lg px-4 py-2.5 text-sm bg-white focus:outline-none focus:border-accent"
         required>
  {% if form.name.errors %}
  <p class="text-xs text-red-600 mt-1">{{ form.name.errors.0 }}</p>
  {% endif %}
</div>
```

## Errores globales del form
```html
{% if form.non_field_errors %}
<div class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
  {% for error in form.non_field_errors %}
  <p>{{ error }}</p>
  {% endfor %}
</div>
{% endif %}
```

## HTMX en formularios
Para busqueda en tiempo real (ejemplo: buscar libros):
```html
<input hx-get="{% url 'books:search' %}"
       hx-trigger="keyup changed delay:400ms"
       hx-target="#results"
       name="book_query"
       autocomplete="off">
<div id="results"></div>
```
La vista retorna un partial HTML, no JSON. HTMX lo inserta directamente.

## Formularios que necesita el proyecto (pendientes)
- **ReportForm** — textarea para la reflexion (solo texto)
- **ReactionForm** — no es form visible, es un boton HTMX POST
- **CommentForm** — textarea para comentarios en reportes
- **DiscussionTopicForm** — textarea para proponer temas de debate
- **VerificationAnswerForm** — inputs para responder preguntas del modo moderado
- **ConfirmReadingForm** — checkbox simple para modo relajado
