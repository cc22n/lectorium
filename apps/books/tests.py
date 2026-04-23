from unittest.mock import patch, MagicMock

from django.test import TestCase

from .models import Book
from .services import search_google_books, get_or_create_from_google


MOCK_API_RESPONSE = {
    "items": [
        {
            "id": "abc123",
            "volumeInfo": {
                "title": "Cien anos de soledad",
                "authors": ["Gabriel Garcia Marquez"],
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9780060883287"}
                ],
                "imageLinks": {
                    "thumbnail": "http://books.google.com/cover.jpg"
                },
            },
        },
        {
            "id": "def456",
            "volumeInfo": {
                "title": "El amor en los tiempos del colera",
                "authors": ["Gabriel Garcia Marquez"],
                "industryIdentifiers": [],
                "imageLinks": {},
            },
        },
    ]
}


class SearchGoogleBooksTests(TestCase):

    @patch("apps.books.services.requests.get")
    def test_returns_parsed_books(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_API_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        results = search_google_books("garcia marquez")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["google_books_id"], "abc123")
        self.assertEqual(results[0]["title"], "Cien anos de soledad")
        self.assertEqual(results[0]["isbn"], "9780060883287")

    @patch("apps.books.services.requests.get")
    def test_cover_url_uses_https(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_API_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        results = search_google_books("garcia marquez")
        self.assertTrue(results[0]["cover_image_url"].startswith("https://"))

    @patch("apps.books.services.requests.get")
    def test_returns_empty_list_on_network_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("timeout")
        results = search_google_books("garcia marquez")
        self.assertEqual(results, [])

    def test_returns_empty_list_without_api_key(self):
        with self.settings(GOOGLE_BOOKS_API_KEY=""):
            results = search_google_books("garcia marquez")
            self.assertEqual(results, [])


class GetOrCreateFromGoogleTests(TestCase):

    def setUp(self):
        self.data = {
            "google_books_id": "abc123",
            "title": "Cien anos de soledad",
            "author": "Gabriel Garcia Marquez",
            "isbn": "9780060883287",
            "cover_image_url": "https://books.google.com/cover.jpg",
        }

    def test_creates_new_book(self):
        book = get_or_create_from_google(self.data)
        self.assertIsInstance(book, Book)
        self.assertEqual(book.google_books_id, "abc123")
        self.assertEqual(book.title, "Cien anos de soledad")

    def test_returns_existing_book_by_google_id(self):
        existing = Book.objects.create(
            google_books_id="abc123",
            title="Cien anos de soledad",
            author="Garcia Marquez",
            is_manual_entry=False,
        )
        book = get_or_create_from_google(self.data)
        self.assertEqual(book.pk, existing.pk)
        self.assertEqual(Book.objects.count(), 1)

    def test_updates_cover_of_existing_book(self):
        existing = Book.objects.create(
            google_books_id="abc123",
            title="Cien anos de soledad",
            author="Garcia Marquez",
            cover_image_url="",
            is_manual_entry=False,
        )
        get_or_create_from_google(self.data)
        existing.refresh_from_db()
        self.assertEqual(existing.cover_image_url, "https://books.google.com/cover.jpg")
