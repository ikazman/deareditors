import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Article, ArticleImage


class ArticlePublicationInvariantTests(TestCase):
    def test_publish_with_update_fields_persists_publication_date(self):
        article = Article.objects.create(title="Черновик", body="Текст")

        article.status = Article.Status.PUBLISHED
        article.save(update_fields=["status"])
        article.refresh_from_db()

        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(article.published_at)

    def test_unpublish_with_update_fields_clears_publication_date(self):
        article = Article.objects.create(
            title="Опубликовано",
            body="Текст",
            status=Article.Status.PUBLISHED,
        )
        self.assertIsNotNone(article.published_at)

        article.status = Article.Status.DRAFT
        article.save(update_fields=["status"])
        article.refresh_from_db()

        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertIsNone(article.published_at)

    def test_database_rejects_published_article_without_publication_date(self):
        article = Article.objects.create(title="Инвариант", body="Текст")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Article.objects.filter(pk=article.pk).update(
                    status=Article.Status.PUBLISHED,
                    published_at=None,
                )


class ScheduledArticleImageVisibilityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp(prefix="deareditors-scheduled-images-")
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        user_model = get_user_model()
        self.reader = user_model.objects.create_user("scheduled-reader", password="secret")
        self.editor = user_model.objects.create_user(
            "scheduled-editor",
            password="secret",
            is_staff=True,
        )
        self.article = Article.objects.create(
            title="Завтрашний материал",
            body="Пока не показываем.",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(days=1),
        )
        self.image = ArticleImage.objects.create(
            article=self.article,
            file=SimpleUploadedFile(
                "future.png",
                b"\x89PNG\r\n\x1a\n" + b"future-image",
                content_type="image/png",
            ),
            alt_text="Будущее изображение",
            content_type="image/png",
        )
        self.url = reverse("article-image", kwargs={"pk": self.image.pk})

    def test_reader_cannot_open_image_before_scheduled_publication(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_editor_can_open_image_before_scheduled_publication(self):
        self.client.force_login(self.editor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        response.close()
