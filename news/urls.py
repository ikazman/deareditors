from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import invite_views, tarot_views, views
from .forms import ReaderAuthenticationForm

urlpatterns = [
    path("health/", views.health, name="health"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="news/login.html",
            authentication_form=ReaderAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("invite/<uuid:token>/", invite_views.invite_accept, name="invite-accept"),
    path(
        "og/invite/<uuid:token>/<int:version>.jpg",
        invite_views.invite_preview,
        name="invite-preview",
    ),
    path(
        "og/invite/<uuid:token>/<int:version>.png",
        invite_views.invite_preview_png_legacy,
        name="invite-preview-png-legacy",
    ),
    path(
        "og/invite/<uuid:token>.png",
        invite_views.invite_preview_legacy,
        name="invite-preview-legacy",
    ),
    path("", views.article_list, name="article-list"),
    path("reader-card/", views.reader_card, name="reader-card"),
    path("letter/", views.letter_create, name="letter-create"),
    path("letter/sent/", views.letter_sent, name="letter-sent"),
    path("images/<uuid:pk>/", views.article_image, name="article-image"),
    path("news/<str:slug>/", views.article_detail, name="article-detail"),
    path(
        "editor/login/",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="editor-login",
    ),
    path("editor/", views.editor_dashboard, name="editor-dashboard"),
    path("editor/tarot/", views.editor_tarot, name="editor-tarot"),
    path(
        "editor/tarot/reroll/",
        tarot_views.editor_tarot_reroll,
        name="editor-tarot-reroll",
    ),
    path("editor/inbox/", views.editor_inbox, name="editor-inbox"),
    path("editor/invites/", views.editor_invitations, name="editor-invitations"),
    path(
        "editor/invites/<int:pk>/revoke/",
        views.editor_invitation_revoke,
        name="editor-invitation-revoke",
    ),
    path("editor/integrations/", views.editor_integrations, name="editor-integrations"),
    path(
        "editor/integrations/mcp/<int:pk>/revoke/",
        views.editor_mcp_key_revoke,
        name="editor-mcp-key-revoke",
    ),
    path("editor/inbox/<int:pk>/review/", views.editor_letter_review, name="editor-letter-review"),
    path("editor/inbox/<int:pk>/convert/", views.editor_letter_convert, name="editor-letter-convert"),
    path("editor/new/", views.editor_article_create, name="editor-article-create"),
    path("editor/<int:pk>/edit/", views.editor_article_edit, name="editor-article-edit"),
    path("editor/<int:pk>/preview/", views.editor_article_preview, name="editor-article-preview"),
    path(
        "editor/<int:pk>/images/upload/",
        views.editor_article_image_upload,
        name="editor-article-image-upload",
    ),
]
