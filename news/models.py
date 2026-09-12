from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


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
