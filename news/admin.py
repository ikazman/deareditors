from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "author_name", "published_at", "updated_at")
    list_filter = ("status", "published_at")
    search_fields = ("title", "lead", "body", "author_name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Материал", {"fields": ("title", "lead", "body")}),
        ("Редакция", {"fields": ("author_name", "status", "published_at", "slug")}),
        ("Служебное", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

admin.site.site_header = "Dear Editors — редакция"
admin.site.site_title = "Dear Editors"
admin.site.index_title = "Редакционный стол"
