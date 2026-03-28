from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("<int:club_pk>/submit/", views.submit_report_view, name="submit"),
    path("<int:club_pk>/", views.report_list_view, name="list"),
    path("<int:club_pk>/topics/add/", views.propose_topic_view, name="propose_topic"),
    path("detail/<int:report_pk>/", views.report_detail_view, name="detail"),
    path("detail/<int:report_pk>/react/", views.toggle_reaction_view, name="react"),
    path("detail/<int:report_pk>/comment/", views.add_comment_view, name="comment"),
    path("<int:club_pk>/discussion/", views.discussion_view, name="discussion"),
    # Verificacion de lectura
    path("<int:club_pk>/verify/", views.verify_view, name="verify"),
    path("<int:club_pk>/verifications/", views.verification_review_view, name="verification_review"),
    path("<int:club_pk>/verifications/<int:answer_pk>/approve/", views.approve_verification_view, name="approve_verification"),
    path("<int:club_pk>/verifications/<int:answer_pk>/reject/", views.reject_verification_view, name="reject_verification"),
    # Moderacion y flags
    path("<int:club_pk>/flag/", views.flag_content_view, name="flag"),
    path("<int:club_pk>/moderation/", views.moderation_view, name="moderation"),
    path("flags/<int:flag_pk>/dismiss/", views.dismiss_flag_view, name="dismiss_flag"),
    path("flags/<int:flag_pk>/delete-content/", views.delete_flagged_content_view, name="delete_flagged_content"),
]
