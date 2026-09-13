import uuid
from datetime import timedelta

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


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    title = models.CharField("заголовок", max_length=220)
    slug = models.SlugField("адрес", max_length=240, unique=True, blank=True, allow_unicode=True)
    lead = models.TextField("лид", blank=True)
    body = models.TextField("текст")
    author_name = models.CharField("автор", max_length=120, default="Дорогая редакция")
    status = models.CharField("статус", max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)
    published_at = models.DateTimeField("опубликовано", blank=True, null=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
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

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        elif self.status == self.Status.DRAFT:
            self.published_at = None

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


class EditorialLetter(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новое"
        REVIEWED = "reviewed", "Просмотрено"

    body = models.TextField("сообщение")
    sender_name = models.CharField("имя", max_length=120, blank=True)
    contact = models.CharField("контакт", max_length=240, blank=True)
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
