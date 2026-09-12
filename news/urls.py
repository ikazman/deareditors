from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import views
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
    path("invite/<uuid:token>/", views.invite_accept, name="invite-accept"),
    path("", views.article_list, name="article-list"),
    path("letter/", views.letter_create, name="letter-create"),
    path("letter/sent/", views.letter_sent, name="letter-sent"),
    path("news/<str:slug>/", views.article_detail, name="article-detail"),
    path(
        "editor/login/",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="editor-login",
    ),
    path("editor/", views.editor_dashboard, name="editor-dashboard"),
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
]
