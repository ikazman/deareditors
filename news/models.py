import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def default_invite_expiry():
    return timezone.now() + timedelta(days=7)


def article_image_upload_path(instance, filename):
    extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(instance.content_type, ".img")
    return f"article-images/{instance.article_id}/{uuid.uuid4().hex}{extension}"


def tarot_card_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".jpg"
    return f"tarot/cards/{uuid.uuid4().hex}{extension}"


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    title = models.CharField("заголовок", max_length=220)
    slug = models.SlugField("адрес", max_length=240, unique=True, blank=True, allow_unicode=True)
    rubric = models.CharField("рубрика", max_length=80, blank=True)
    lead = models.TextField("лид", blank=True)
    body = models.TextField("текст")
    author_name = models.CharField("автор", max_length=120, default="Дорогая редакция")
    status = models.CharField("статус", max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)
    published_at = models.DateTimeField("опубликовано", blank=True, null=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="draft", published_at__isnull=True)
                    | models.Q(status="published", published_at__isnull=False)
                ),
                name="article_status_publication_date_consistent",
            )
        ]
        verbose_name = "публикация"
        verbose_name_plural = "публикации"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "material"
            candidate = base
            counter = 2
            while Article.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate

        publication_date_changed = False
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
            publication_date_changed = True
        elif self.status == self.Status.DRAFT and self.published_at is not None:
            self.published_at = None
            publication_date_changed = True

        if publication_date_changed and kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"published_at"}

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("article-detail", kwargs={"slug": self.slug})


class ArticleImage(models.Model):
    class Layout(models.TextChoices):
        MEASURE = "measure", "В колонку"
        WIDE = "wide", "Шире текста"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(
        Article,
        verbose_name="материал",
        related_name="images",
        on_delete=models.CASCADE,
    )
    marker_index = models.PositiveIntegerField("номер в тексте", editable=False)
    file = models.FileField("изображение", upload_to=article_image_upload_path, max_length=255)
    caption = models.CharField("подпись", max_length=500, blank=True)
    alt_text = models.CharField("описание", max_length=240)
    layout = models.CharField("ширина", max_length=12, choices=Layout.choices, default=Layout.MEASURE)
    content_type = models.CharField("тип файла", max_length=32, editable=False)
    created_at = models.DateTimeField("загружено", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("article", "marker_index"),
                name="unique_article_image_marker_index",
            )
        ]
        verbose_name = "изображение материала"
        verbose_name_plural = "изображения материала"

    def __str__(self):
        return self.caption or f"Изображение {self.marker_index}"

    def save(self, *args, **kwargs):
        if self.marker_index is None:
            current_max = (
                ArticleImage.objects.filter(article_id=self.article_id).aggregate(
                    max_index=models.Max("marker_index")
                )["max_index"]
                or 0
            )
            self.marker_index = current_max + 1
        super().save(*args, **kwargs)

    @property
    def marker(self):
        return f"[[фото {self.marker_index}]]"

    def get_absolute_url(self):
        return reverse("article-image", kwargs={"pk": self.pk})


@receiver(post_delete, sender=ArticleImage)
def delete_article_image_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.storage.delete(instance.file.name)


class TarotCard(models.Model):
    name = models.CharField("карта", max_length=120, unique=True)
    description = models.TextField("описание", blank=True)
    check_words = models.TextField("ключевые слова", blank=True)
    prophecy = models.TextField("прогноз", blank=True)
    meaning_straight = models.TextField("прямое значение")
    meaning_reversed = models.TextField("перевернутое значение")
    image = models.FileField("изображение карты", upload_to=tarot_card_upload_path, max_length=255)

    class Meta:
        ordering = ["name"]
        verbose_name = "карта Таро"
        verbose_name_plural = "карты Таро"

    def __str__(self):
        return self.name


@receiver(post_delete, sender=TarotCard)
def delete_tarot_card_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.storage.delete(instance.image.name)


class TarotDraw(models.Model):
    class Position(models.TextChoices):
        STRAIGHT = "straight", "Прямая"
        REVERSED = "reversed", "Перевернутая"

    draw_date = models.DateField("дата", unique=True)
    question = models.CharField("вопрос", max_length=240)
    card_name = models.CharField("карта", max_length=120)
    position = models.CharField("положение", max_length=12, choices=Position.choices)
    check_words = models.TextField("ключевые слова", blank=True)
    prophecy = models.TextField("прогноз", blank=True)
    meaning = models.TextField("значение")
    article = models.OneToOneField(
        Article,
        verbose_name="черновик",
        related_name="tarot_draw",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        ordering = ["-draw_date"]
        verbose_name = "карта дня"
        verbose_name_plural = "карты дня"

    def __str__(self):
        return f"{self.draw_date:%d.%m.%Y} — {self.card_name}"


class EditorialLetter(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новое"
        REVIEWED = "reviewed", "Просмотрено"

    body = models.TextField("сообщение")
    sender_name = models.CharField("имя", max_length=120, blank=True)
    contact = models.CharField("контакт", max_length=240, blank=True)
    anonymity_requested = models.BooleanField("не называть автора", default=False)
    sender_fingerprint = models.CharField(
        "анонимный отпечаток отправителя",
        max_length=64,
        blank=True,
        editable=False,
    )
    status = models.CharField("статус", max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField("получено", auto_now_add=True)
    reviewed_at = models.DateTimeField("просмотрено", blank=True, null=True)
    converted_article = models.OneToOneField(
        Article,
        verbose_name="созданный черновик",
        related_name="source_letter",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "письмо в редакцию"
        verbose_name_plural = "письма в редакцию"

    def __str__(self):
        sender = self.sender_name or "анонимно"
        return f"{sender}: {self.body[:60]}"


class Invitation(models.Model):
    token = models.UUIDField("токен", default=uuid.uuid4, unique=True, editable=False)
    label = models.CharField("для кого", max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="создал",
        related_name="created_invitations",
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField("создано", auto_now_add=True)
    expires_at = models.DateTimeField("действует до", default=default_invite_expiry)
    accepted_at = models.DateTimeField("принято", blank=True, null=True)
    accepted_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="принял",
        related_name="accepted_invitation",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    revoked_at = models.DateTimeField("отозвано", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "приглашение"
        verbose_name_plural = "приглашения"

    def __str__(self):
        return self.label or str(self.token)

    @property
    def is_active(self):
        return self.accepted_at is None and self.revoked_at is None and self.expires_at > timezone.now()

    def get_absolute_url(self):
        return reverse("invite-accept", kwargs={"token": self.token})


class MCPAccessKey(models.Model):
    label = models.CharField("название", max_length=120)
    prefix = models.CharField("префикс", max_length=16, unique=True)
    key_hash = models.CharField("хеш ключа", max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="создал",
        related_name="created_mcp_keys",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("создано", auto_now_add=True)
    last_used_at = models.DateTimeField("последнее использование", blank=True, null=True)
    revoked_at = models.DateTimeField("отозвано", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ключ MCP"
        verbose_name_plural = "ключи MCP"

    def __str__(self):
        return self.label

    @property
    def is_active(self):
        return self.revoked_at is None

    @property
    def masked(self):
        return f"de_mcp_{self.prefix}_…"


class ReaderArticleView(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="читатель",
        related_name="article_views",
        on_delete=models.CASCADE,
    )
    article = models.ForeignKey(
        Article,
        verbose_name="материал",
        related_name="reader_views",
        on_delete=models.CASCADE,
    )
    first_opened_at = models.DateTimeField("первое открытие", default=timezone.now)
    last_opened_at = models.DateTimeField("последнее открытие", default=timezone.now)
    open_count = models.PositiveIntegerField("открытий", default=1)

    class Meta:
        ordering = ["-last_opened_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "article"),
                name="unique_reader_article_view",
            )
        ]
        verbose_name = "просмотр материала читателем"
        verbose_name_plural = "просмотры материалов читателями"

    def __str__(self):
        return f"{self.user} — {self.article} ({self.open_count})"


class ReaderDailyVisit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="читатель",
        related_name="reader_daily_visits",
        on_delete=models.CASCADE,
    )
    visit_date = models.DateField("дата посещения", default=timezone.localdate)
    created_at = models.DateTimeField("зафиксировано", auto_now_add=True)

    class Meta:
        ordering = ["-visit_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "visit_date"),
                name="unique_reader_daily_visit",
            )
        ]
        verbose_name = "день посещения читателя"
        verbose_name_plural = "дни посещений читателей"

    def __str__(self):
        return f"{self.user} — {self.visit_date:%d.%m.%Y}"


class ReaderProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="читатель",
        related_name="reader_profile",
        on_delete=models.CASCADE,
    )
    ticket_number = models.CharField("номер билета", max_length=10, unique=True, editable=False)
    issued_at = models.DateTimeField("выдан", default=timezone.now)
    cover_key = models.CharField("обложка", max_length=32, default="classic")

    class Meta:
        verbose_name = "читательский билет"
        verbose_name_plural = "читательские билеты"

    def __str__(self):
        return f"{self.ticket_number} — {self.user}"


class AchievementUnlock(models.Model):
    class Code(models.TextChoices):
        CORRESPONDENT_III = "correspondent_iii", "Корреспондент III степени"
        CORRESPONDENT_II = "correspondent_ii", "Корреспондент II степени"
        CORRESPONDENT_I = "correspondent_i", "Корреспондент I степени"
        PERMANENT_READER = "permanent_reader", "Постоянный читатель"
        ANONYMOUS_SOURCE = "anonymous_source", "Источник, пожелавший остаться неизвестным"
        COMPLETE_MONTH = "complete_month", "Читатель без пропусков"
        ARCHIVE_READER = "archive_reader", "Читатель архива"
        CARD_DAY_SUBSCRIBER = "card_day_subscriber", "Постоянный подписчик рубрики"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="читатель",
        related_name="reader_marks",
        on_delete=models.CASCADE,
    )
    code = models.CharField("отметка", max_length=32, choices=Code.choices)
    title = models.CharField("название при выдаче", max_length=160, editable=False)
    description = models.TextField("основание при выдаче", editable=False)
    unlocked_at = models.DateTimeField("зафиксировано", default=timezone.now)

    class Meta:
        ordering = ["unlocked_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "code"),
                name="unique_reader_achievement_unlock",
            )
        ]
        verbose_name = "отметка редакции"
        verbose_name_plural = "отметки редакции"

    def __str__(self):
        return f"{self.title} — {self.user}"
