# Skill: Backend Django — Patrones del proyecto

## Estructura de apps
Todas las apps van en `apps/`. Cada app tiene: models.py, views.py, urls.py, forms.py, admin.py, apps.py, tests.py.

## Modelos
- Siempre usar `verbose_name` en espanol sin acentos en campos
- Usar `related_name` explicito en todas las FK
- Constraints con `UniqueConstraint` en lugar de `unique_together`
- Usar `TextChoices` para campos con opciones fijas
- Propiedades calculadas como `@property` en el modelo
- Logica de negocio en metodos del modelo, no en las vistas

## Vistas
- Preferir vistas basadas en funciones (FBV) sobre clases (CBV) para claridad
- Excepciones: LoginView, LogoutView de Django auth
- Siempre usar `@login_required` donde aplique
- Usar `get_object_or_404` para buscar objetos
- Usar `select_related` y `prefetch_related` en queries
- Validar permisos al inicio de la vista antes de hacer cualquier cosa
- Mensajes con `django.contrib.messages` para feedback al usuario

## Forms
- Usar `forms.Form` cuando el formulario no mapea 1:1 al modelo
- Usar `forms.ModelForm` para CRUD simple
- Validacion custom en `clean_FIELD()` o `clean()`
- Nunca confiar en datos del cliente, siempre validar en el servidor

## URLs
- Namespace por app: `app_name = "apps_name"`
- Patron: `path("<int:pk>/action/", view, name="action")`
- El home del sitio esta en clubs:home (raiz /)

## Tareas Celery
- Definir en `tasks.py` dentro de cada app
- Usar `@shared_task` para que Celery las descubra
- Tareas periodicas se configuran en Celery Beat via admin o settings
- Las transiciones de fase van en `apps/clubs/tasks.py`

## Seguridad
- CSRF token en todos los forms ({% csrf_token %})
- HTMX headers incluyen CSRF via `hx-headers` en base.html
- Nunca exponer IDs internos sensibles
- Validar que el usuario tiene permiso para la accion antes de ejecutar
- Usar `on_delete=PROTECT` para relaciones criticas (Club->Book, Club->Creator)

## Base de datos
- PostgreSQL con psycopg v3
- Usar `update_fields` en save() cuando sea posible
- Transacciones con `transaction.atomic()` para operaciones que tocan varias tablas
- Indices: status de Club ya tiene db_index=True

## Ejemplo de patron de vista completo
```python
@login_required
def my_view(request, pk):
    obj = get_object_or_404(MyModel.objects.select_related("fk"), pk=pk)

    # Validar permisos
    if not obj.can_user_do_action(request.user):
        messages.error(request, "No tienes permiso.")
        return redirect("somewhere")

    if request.method == "POST":
        form = MyForm(request.POST)
        if form.is_valid():
            # Logica
            messages.success(request, "Exito!")
            return redirect("somewhere")
    else:
        form = MyForm()

    return render(request, "app/template.html", {"obj": obj, "form": form})
```
