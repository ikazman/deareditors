from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.article_list, name="article-list"),
    path("letter/", views.letter_create, name="letter-create"),
    path("letter/sent/", views.letter_sent, name="letter-sent"),
    path("news/<str:slug>/", views.article_detail, name="article-detail"),
    path(
        "editor/login/",
        auth_views.LoginView.as_view(
            template_name="editor/login.html",
            redirect_authenticated_user=True,
        ),
        name="editor-login",
    ),
    path("editor/logout/", views.editor_logout, name="editor-logout"),
    path("editor/", views.editor_dashboard, name="editor-dashboard"),
    path("editor/inbox/", views.editor_inbox, name="editor-inbox"),
    path("editor/inbox/<int:pk>/review/", views.editor_letter_review, name="editor-letter-review"),
    path("editor/inbox/<int:pk>/convert/", views.editor_letter_convert, name="editor-letter-convert"),
    path("editor/new/", views.editor_article_create, name="editor-article-create"),
    path("editor/<int:pk>/edit/", views.editor_article_edit, name="editor-article-edit"),
]
