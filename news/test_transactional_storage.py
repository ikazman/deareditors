import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TransactionTestCase, override_settings

from .models import Article, ArticleImage, TarotCard


class TransactionalStorageCleanupTests(TransactionTestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="deareditors-transactional-media-")
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)
        super().tearDown()

    def test_article_image_file_survives_rolled_back_delete(self):
        article = Article.objects.create(title="Откат", body="Текст")
        image = ArticleImage.objects.create(
            article=article,
            file=SimpleUploadedFile("rollback.png", b"image-bytes", content_type="image/png"),
            alt_text="Проверка отката",
            content_type="image/png",
        )
        image_pk = image.pk
        storage = image.file.storage
        name = image.file.name
        self.assertTrue(storage.exists(name))

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                image.delete()
                self.assertTrue(storage.exists(name))
                raise RuntimeError("rollback")

        self.assertTrue(ArticleImage.objects.filter(pk=image_pk).exists())
        self.assertTrue(storage.exists(name))

    def test_article_image_file_is_deleted_after_commit(self):
        article = Article.objects.create(title="Коммит", body="Текст")
        image = ArticleImage.objects.create(
            article=article,
            file=SimpleUploadedFile("commit.png", b"image-bytes", content_type="image/png"),
            alt_text="Проверка коммита",
            content_type="image/png",
        )
        storage = image.file.storage
        name = image.file.name

        with transaction.atomic():
            image.delete()
            self.assertTrue(storage.exists(name))

        self.assertFalse(storage.exists(name))

    def test_tarot_card_file_survives_rolled_back_delete(self):
        card = TarotCard.objects.create(
            name="Тестовая карта",
            description="",
            check_words="",
            prophecy="",
            meaning_straight="Прямое",
            meaning_reversed="Перевернутое",
            image=SimpleUploadedFile("card.jpg", b"card-bytes", content_type="image/jpeg"),
        )
        card_pk = card.pk
        storage = card.image.storage
        name = card.image.name

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                card.delete()
                self.assertTrue(storage.exists(name))
                raise RuntimeError("rollback")

        self.assertTrue(TarotCard.objects.filter(pk=card_pk).exists())
        self.assertTrue(storage.exists(name))
