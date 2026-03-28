from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Accede a un valor de un diccionario por clave variable en templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


@register.filter
def get_index(lst, index):
    """Accede a un elemento de una lista por indice (string o int)."""
    try:
        return lst[int(index)]
    except (IndexError, ValueError, TypeError):
        return ""
