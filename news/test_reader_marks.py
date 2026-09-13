from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AchievementUnlock, Article, EditorialLetter
from .reader_identity import reader_fingerprint


class ReaderMarksTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.reader = user_model.objects.create_user(
            username="reader-marks",
            password="reader-marks-pass-9182",
            first_name="Мария",
        )
        self.other_reader = user_model.objects.create_user(
            username="other-reader-marks",
            password="other-reader-marks-pass-9182",
        )

    def test_letter_stores_only_stable_opaque_sender_fingerprint(self):
        self.client.force_login(self.reader)

        first_response = self.client.post(
            reverse("letter-create"),
            {"body": "Первый слух", "sender_name": "", "contact": ""},
        )
        second_response = self.client.post(
            reverse("letter-create"),
            {"body": "Второй слух", "sender_name": "", "contact": ""},
        )

        self.assertRedirects(first_response, reverse("letter-sent"))
        self.assertRedirects(second_response, reverse("letter-sent"))
        letters = list(EditorialLetter.objects.order_by("pk"))
        self.assertEqual(letters[0].sender_fingerprint, letters[1].sender_fingerprint)
        self.assertEqual(letters[0].sender_fingerprint, reader_fingerprint(self.reader))
        self.assertEqual(len(letters[0].sender_fingerprint), 64)
        self.assertNotIn(self.reader.username, letters[0].sender_fingerprint)
        self.assertNotEqual(
            letters[0].sender_fingerprint,
            reader_fingerprint(self.other_reader),
        )
        self.assertNotIn("submitted_by", {field.name for field in EditorialLetter._meta.fields})

    def test_first_used_letter_awards_correspondent_third_degree(self):
        article = Article.objects.create(
            title="Материал из письма",
            body="Редакция использовала письмо.",
            status=Article.Status.PUBLISHED,
        )
        EditorialLetter.objects.create(
            body="Слух",
            sender_fingerprint=reader_fingerprint(self.reader),
            converted_article=article,
        )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        mark = AchievementUnlock.objects.get(
            user=self.reader,
            code=AchievementUnlock.Code.CORRESPONDENT_III,
        )
        self.assertEqual(mark.unlocked_at, article.published_at)
        self.assertContains(response, "Корреспондент III степени")
        self.assertContains(response, "Письмо предъявителя использовано редакцией.")
        self.assertFalse(
            AchievementUnlock.objects.filter(
                user=self.reader,
                code=AchievementUnlock.Code.CORRESPONDENT_II,
            ).exists()
        )

    def test_third_used_letter_awards_second_degree(self):
        fingerprint = reader_fingerprint(self.reader)
        articles = []
        for index in range(3):
            article = Article.objects.create(
                title=f"Материал {index}",
                body="Редакция использовала письмо.",
                status=Article.Status.PUBLISHED,
            )
            articles.append(article)
            EditorialLetter.objects.create(
                body=f"Слух {index}",
                sender_fingerprint=fingerprint,
                converted_article=article,
            )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        second_degree = AchievementUnlock.objects.get(
            user=self.reader,
            code=AchievementUnlock.Code.CORRESPONDENT_II,
        )
        self.assertEqual(second_degree.unlocked_at, articles[2].published_at)
        self.assertContains(response, "Корреспондент III степени")
        self.assertContains(response, "Корреспондент II степени")
        self.assertContains(response, "Использовано третье письмо предъявителя.")

    def test_draft_and_legacy_unlinked_letters_do_not_award_marks(self):
        draft = Article.objects.create(
            title="Еще черновик",
            body="Публикации пока нет.",
            status=Article.Status.DRAFT,
        )
        EditorialLetter.objects.create(
            body="Письмо текущего читателя",
            sender_fingerprint=reader_fingerprint(self.reader),
            converted_article=draft,
        )
        published = Article.objects.create(
            title="Старое письмо",
            body="Автор старого письма системе неизвестен.",
            status=Article.Status.PUBLISHED,
        )
        EditorialLetter.objects.create(
            body="Историческое письмо без отпечатка",
            converted_article=published,
        )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        self.assertFalse(AchievementUnlock.objects.filter(user=self.reader).exists())
        self.assertContains(response, "Пока без отметок. Редакция продолжает наблюдение.")
