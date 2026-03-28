from django.contrib import admin
from .models import (
    Report, Reaction, Comment, DiscussionTopic,
    VerificationAnswer, ContentFlag,
)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "is_late", "submitted_at")
    list_filter = ("is_late", "submitted_at")
    search_fields = ("user__username", "club__name", "text")
    readonly_fields = ("submitted_at",)


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("user", "report", "type", "created_at")
    list_filter = ("type",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "report", "created_at")
    search_fields = ("user__username", "text")


@admin.register(DiscussionTopic)
class DiscussionTopicAdmin(admin.ModelAdmin):
    list_display = ("club", "user", "text", "created_at")
    search_fields = ("text", "club__name")


@admin.register(VerificationAnswer)
class VerificationAnswerAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "passed", "submitted_at")
    list_filter = ("passed",)


@admin.register(ContentFlag)
class ContentFlagAdmin(admin.ModelAdmin):
    list_display = ("reported_by", "content_type", "content_id", "resolved", "created_at")
    list_filter = ("content_type", "resolved")
