from django.urls import path

from . import views


urlpatterns = [
    path("wordly/", views.wordly_archive, name="wordly"),
    path(
        "wordly/<int:year>/<int:month>/<int:day>/",
        views.wordly_play,
        name="wordly-play",
    ),
    path("editor/wordly/", views.editor_wordly, name="editor-wordly"),
]
