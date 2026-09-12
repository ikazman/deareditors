from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.article_list, name="article-list"),
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
    path("editor/new/", views.editor_article_create, name="editor-article-create"),
    path("editor/<int:pk>/edit/", views.editor_article_edit, name="editor-article-edit"),
]
