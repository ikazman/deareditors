from django.urls import path

from . import views

urlpatterns = [
    path("", views.article_list, name="article-list"),
    path("news/<str:slug>/", views.article_detail, name="article-detail"),
]
