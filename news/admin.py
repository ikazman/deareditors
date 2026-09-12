from django.contrib import admin

from .models import Article, EditorialLetter, Invitation


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


@admin.register(EditorialLetter)
class EditorialLetterAdmin(admin.ModelAdmin):
    list_display = ("sender_name", "status", "created_at", "reviewed_at", "converted_article")
    list_filter = ("status", "created_at")
    search_fields = ("body", "sender_name", "contact")
    readonly_fields = ("created_at", "reviewed_at", "converted_article")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("label", "created_by", "created_at", "expires_at", "accepted_by", "revoked_at")
    search_fields = ("label", "accepted_by__username", "accepted_by__first_name")
    readonly_fields = ("token", "created_at", "accepted_at", "accepted_by", "revoked_at")


admin.site.site_header = "Dear Editors — редакция"
admin.site.site_title = "Dear Editors"
admin.site.index_title = "Редакционный стол"
