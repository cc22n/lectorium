"""
Servicio de integracion con Google Books API.
Busca libros y los persiste en la BD local.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


def search_google_books(query: str, max_results: int = 8) -> list[dict]:
    """
    Busca libros en Google Books API.
    Retorna lista de dicts con: google_books_id, title, author, isbn, cover_image_url.
    Devuelve [] si la API key no esta configurada o si hay un error de red.
    """
    api_key = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
    if not api_key or not query:
        return []

    params = {
        "q": query,
        "key": api_key,
        "maxResults": max_results,
        "printType": "books",
    }

    try:
        response = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Google Books API error: %s", exc)
        return []
    except ValueError:
        logger.warning("Google Books API: respuesta JSON invalida")
        return []

    results = []
    for item in data.get("items", []):
        volume = item.get("volumeInfo", {})

        # ISBN: preferir ISBN-13
        isbn = ""
        for identifier in volume.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_13":
                isbn = identifier["identifier"]
                break
            if identifier.get("type") == "ISBN_10" and not isbn:
                isbn = identifier["identifier"]

        # Portada: usar HTTPS siempre
        image_links = volume.get("imageLinks", {})
        cover = image_links.get("thumbnail") or image_links.get("smallThumbnail") or ""
        if cover:
            cover = cover.replace("http://", "https://")

        results.append({
            "google_books_id": item["id"],
            "title": volume.get("title") or "Sin titulo",
            "author": ", ".join(volume.get("authors") or ["Autor desconocido"]),
            "isbn": isbn,
            "cover_image_url": cover,
        })

    return results


def get_or_create_from_google(data: dict):
    """
    Crea o recupera un Book a partir de datos de Google Books.
    Evita duplicados usando google_books_id.
    Actualiza la portada si el libro ya existe pero no tiene imagen.
    Retorna el objeto Book guardado.
    """
    from .models import Book

    google_id = data.get("google_books_id") or None

    if google_id:
        book = Book.objects.filter(google_books_id=google_id).first()
        if book:
            if not book.cover_image_url and data.get("cover_image_url"):
                book.cover_image_url = data["cover_image_url"]
                book.save(update_fields=["cover_image_url"])
            return book

    book = Book.objects.create(
        google_books_id=google_id,
        title=data.get("title", "Sin titulo"),
        author=data.get("author", "Autor desconocido"),
        isbn=data.get("isbn", ""),
        cover_image_url=data.get("cover_image_url", ""),
        is_manual_entry=False,
    )
    return book
