from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import ManualBookForm
from .models import Book
from .services import search_google_books, get_or_create_from_google


def book_search_view(request):
    """
    HTMX endpoint: busca libros primero en BD local, luego en Google Books API
    si los resultados locales son insuficientes.
    """
    query = request.GET.get("book_query", "").strip()
    local_books = []
    api_books = []

    if len(query) >= 2:
        local_books = list(
            Book.objects.filter(
                Q(title__icontains=query) | Q(author__icontains=query)
            )[:6]
        )

        # Complementar con Google Books si hay pocos resultados locales
        if len(local_books) < 4:
            api_results = search_google_books(query, max_results=8)
            # Excluir los que ya estan en local (por google_books_id)
            local_gids = {b.google_books_id for b in local_books if b.google_books_id}
            api_books = [b for b in api_results if b["google_books_id"] not in local_gids]

    return render(request, "books/search_results.html", {
        "local_books": local_books,
        "api_books": api_books,
        "query": query,
    })


@login_required
@require_POST
def save_google_book_view(request):
    """
    Guarda un libro de Google Books en la BD local y devuelve un snippet JS
    que actualiza la seleccion de libro en el formulario de crear club.
    Llamado via HTMX POST cuando el usuario elige un resultado de la API.
    """
    data = {
        "google_books_id": request.POST.get("google_books_id", "").strip(),
        "title": request.POST.get("title", "").strip(),
        "author": request.POST.get("author", "").strip(),
        "isbn": request.POST.get("isbn", "").strip(),
        "cover_image_url": request.POST.get("cover_image_url", "").strip(),
    }

    if not data["title"]:
        return HttpResponse(status=400)

    book = get_or_create_from_google(data)

    # Devuelve JS que reutiliza la funcion selectBook ya definida en el template
    from django.utils.html import escapejs
    title_js = escapejs(book.title)
    author_js = escapejs(book.author)
    return HttpResponse(
        f"<script>selectBook('{book.pk}', '{title_js}', '{author_js}');</script>",
        content_type="text/html",
    )


@login_required
def manual_create_view(request):
    """Registro manual de un libro que no esta en Google Books."""
    if request.method == "POST":
        form = ManualBookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.is_manual_entry = True
            book.created_by = request.user
            book.save()
            messages.success(
                request,
                f"Libro '{book.title}' registrado. Ya puedes usarlo al crear un club."
            )
            return redirect("clubs:create")
    else:
        form = ManualBookForm()

    return render(request, "books/manual_create.html", {"form": form})
