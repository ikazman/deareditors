from django.urls import path

from . import views

urlpatterns = [
    path("menu/", views.menu_today, name="menu-today"),
    path("menu/<date:menu_date>/", views.menu_detail, name="menu-detail"),
    path("editor/menu/", views.editor_menu, name="editor-menu"),
]
