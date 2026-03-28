from django.contrib import admin
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_manual_entry", "google_books_id", "created_at")
    list_filter = ("is_manual_entry",)
    search_fields = ("title", "author", "isbn")
    readonly_fields = ("created_at",)
