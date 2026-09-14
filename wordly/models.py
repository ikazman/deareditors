from django.conf import settings
from django.db import models


class DailyWord(models.Model):
    date = models.DateField("дата", unique=True)
    word = models.CharField("слово", max_length=5)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "слово дня"
        verbose_name_plural = "слова дня"

    def __str__(self):
        return f"{self.date:%d.%m.%Y} — {self.word}"


class WordlyGame(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="читатель",
        related_name="wordly_games",
        on_delete=models.CASCADE,
    )
    daily_word = models.ForeignKey(
        DailyWord,
        verbose_name="слово дня",
        related_name="games",
        on_delete=models.CASCADE,
    )
    guesses = models.JSONField("попытки", default=list)
    won = models.BooleanField("угадано", default=False)
    completed_at = models.DateTimeField("завершено", blank=True, null=True)
    created_at = models.DateTimeField("начато", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)

    class Meta:
        ordering = ["-daily_word__date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "daily_word"),
                name="unique_wordly_game_per_reader_and_day",
            )
        ]
        verbose_name = "партия Вордли"
        verbose_name_plural = "партии Вордли"

    def __str__(self):
        return f"{self.user} — {self.daily_word.date:%d.%m.%Y}"
