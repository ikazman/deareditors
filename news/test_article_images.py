import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Article, ArticleImage
from .templatetags.editorial_markdown import editorial_article


class ArticleImageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp(prefix="deareditors-images-")
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user("editor", password="secret", is_staff=True)
        self.reader = user_model.objects.create_user("reader", password="secret")
        self.article = Article.objects.create(
            title="Изображение дня",
            body="Редакция располагает изображением.",
            author_name="Дорогая редакция",
        )

    def _png(self, name="example.png"):
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\n" + b"test-image-bytes",
            content_type="image/png",
        )

    def test_editor_can_upload_image_and_receive_readable_marker(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("editor-article-image-upload", kwargs={"pk": self.article.pk}),
            {
                "file": self._png(),
                "caption": "Фото предоставлено источником, пожелавшим остаться в столовой.",
                "alt_text": "Кот смотрит в сторону",
                "layout": ArticleImage.Layout.WIDE,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        image = ArticleImage.objects.get()
        self.assertEqual(image.marker_index, 1)
        self.assertEqual(image.marker, "[[фото 1]]")
        self.assertEqual(payload["marker"], "[[фото 1]]")
        self.assertEqual(image.content_type, "image/png")
        self.assertEqual(image.layout, ArticleImage.Layout.WIDE)
        self.assertTrue(image.file.name.endswith(".png"))

    def test_photo_numbers_do_not_shift_after_deletion(self):
        first = ArticleImage.objects.create(
            article=self.article,
            file="article-images/one.png",
            alt_text="Первое",
            content_type="image/png",
        )
        second = ArticleImage.objects.create(
            article=self.article,
            file="article-images/two.png",
            alt_text="Второе",
            content_type="image/png",
        )
        self.assertEqual(first.marker, "[[фото 1]]")
        self.assertEqual(second.marker, "[[фото 2]]")

        first.delete()
        third = ArticleImage.objects.create(
            article=self.article,
            file="article-images/three.png",
            alt_text="Третье",
            content_type="image/png",
        )
        self.assertEqual(second.marker, "[[фото 2]]")
        self.assertEqual(third.marker, "[[фото 3]]")

    def test_upload_rejects_non_image_content(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("editor-article-image-upload", kwargs={"pk": self.article.pk}),
            {
                "file": SimpleUploadedFile("not-an-image.png", b"plain text", content_type="image/png"),
                "alt_text": "Не изображение",
                "layout": ArticleImage.Layout.MEASURE,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ArticleImage.objects.count(), 0)

    def test_draft_image_is_editor_only_then_available_to_reader_after_publish(self):
        image = ArticleImage.objects.create(
            article=self.article,
            file=self._png(),
            caption="",
            alt_text="Тестовое изображение",
            layout=ArticleImage.Layout.MEASURE,
            content_type="image/png",
        )
        url = reverse("article-image", kwargs={"pk": image.pk})

        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.force_login(self.editor)
        editor_response = self.client.get(url)
        self.assertEqual(editor_response.status_code, 200)
        self.assertEqual(editor_response["Cache-Control"], "private, no-store")
        editor_response.close()

        self.article.status = Article.Status.PUBLISHED
        self.article.save()
        self.client.force_login(self.reader)
        reader_response = self.client.get(url)
        self.assertEqual(reader_response.status_code, 200)
        reader_response.close()

    def test_article_renderer_inserts_only_owned_image_and_escapes_caption(self):
        image = ArticleImage.objects.create(
            article=self.article,
            file="article-images/example.png",
            caption="Источник <не назван>",
            alt_text='Кадр с "важным" выражением лица',
            layout=ArticleImage.Layout.WIDE,
            content_type="image/png",
        )
        foreign_article = Article.objects.create(title="Чужой материал", body="Текст")
        foreign_image = ArticleImage.objects.create(
            article=foreign_article,
            file="article-images/foreign.png",
            caption="Чужая подпись",
            alt_text="Чужое изображение",
            content_type="image/png",
        )
        foreign_legacy_marker = f"[[image:{foreign_image.pk}]]"
        self.article.body = f"До изображения.\n\n{image.marker}\n\nПосле изображения.\n\n{foreign_legacy_marker}"
        self.article.save()

        html = str(editorial_article(self.article))
        self.assertIn("article-figure--wide", html)
        self.assertIn(reverse("article-image", kwargs={"pk": image.pk}), html)
        self.assertIn("Источник &lt;не назван&gt;", html)
        self.assertNotIn("Чужая подпись", html)
        self.assertNotIn(reverse("article-image", kwargs={"pk": foreign_image.pk}), html)
        self.assertIn("До изображения.", html)
        self.assertIn("После изображения.", html)

    def test_legacy_uuid_marker_for_owned_image_still_renders(self):
        image = ArticleImage.objects.create(
            article=self.article,
            file="article-images/legacy.png",
            alt_text="Старый маркер",
            content_type="image/png",
        )
        self.article.body = f"[[image:{image.pk}]]"
        self.article.save()

        html = str(editorial_article(self.article))
        self.assertIn(reverse("article-image", kwargs={"pk": image.pk}), html)
