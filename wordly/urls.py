from django.urls import path

from . import views


urlpatterns = [
    path("wordly/", views.wordly, name="wordly"),
    path("editor/wordly/", views.editor_wordly, name="editor-wordly"),
]
