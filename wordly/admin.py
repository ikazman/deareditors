from django.contrib import admin

from .models import DailyWord, WordlyGame


@admin.register(DailyWord)
class DailyWordAdmin(admin.ModelAdmin):
    list_display = ("date", "word", "updated_at")
    ordering = ("-date",)


@admin.register(WordlyGame)
class WordlyGameAdmin(admin.ModelAdmin):
    list_display = ("user", "daily_word", "won", "completed_at")
    list_filter = ("won", "daily_word__date")
    search_fields = ("user__username",)
