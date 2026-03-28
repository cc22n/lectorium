from django.contrib import admin
from .models import Club, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    readonly_fields = ("joined_at",)


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = (
        "name", "book", "status", "mode", "language",
        "active_members_count", "min_members", "max_members", "created_at",
    )
    list_filter = ("status", "mode", "language")
    search_fields = ("name", "book__title", "creator__username")
    readonly_fields = (
        "created_at", "updated_at",
        "reading_starts_at", "submission_starts_at",
        "review_starts_at", "discussion_starts_at", "closes_at",
    )
    inlines = [MembershipInline]
    fieldsets = (
        ("Información básica", {
            "fields": ("name", "description", "book", "creator", "language"),
        }),
        ("Configuración", {
            "fields": ("mode", "status", "min_members", "max_members"),
        }),
        ("Duraciones (días)", {
            "fields": (
                "reading_duration_days", "submission_duration_days",
                "review_duration_days", "discussion_duration_days",
            ),
        }),
        ("Fechas de fase", {
            "fields": (
                "open_until", "reading_starts_at", "submission_starts_at",
                "review_starts_at", "discussion_starts_at", "closes_at",
            ),
        }),
        ("Modo moderado", {
            "fields": ("verification_questions",),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__username", "club__name")
