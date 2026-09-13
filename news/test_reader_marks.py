from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AchievementUnlock, Article, EditorialLetter, ReaderArticleView
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

    def _published_article(self, title, *, published_at=None, rubric=""):
        article = Article.objects.create(
            title=title,
            body="Редакция фиксирует обстоятельства.",
            rubric=rubric,
            status=Article.Status.PUBLISHED,
        )
        if published_at is not None:
            Article.objects.filter(pk=article.pk).update(published_at=published_at)
            article.refresh_from_db()
        return article

    def test_letter_stores_only_stable_opaque_sender_fingerprint(self):
        self.client.force_login(self.reader)

        first_response = self.client.post(
            reverse("letter-create"),
            {"body": "Первый слух", "sender_name": "", "contact": "", "anonymity_requested": False},
        )
        second_response = self.client.post(
            reverse("letter-create"),
            {"body": "Второй слух", "sender_name": "", "contact": "", "anonymity_requested": False},
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
        article = self._published_article("Материал из письма")
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
            article = self._published_article(f"Материал {index}")
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

    def test_tenth_used_letter_awards_first_degree(self):
        fingerprint = reader_fingerprint(self.reader)
        articles = []
        for index in range(10):
            article = self._published_article(f"Корреспондентский материал {index + 1}")
            articles.append(article)
            EditorialLetter.objects.create(
                body=f"Корреспондентский слух {index + 1}",
                sender_fingerprint=fingerprint,
                converted_article=article,
            )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        first_degree = AchievementUnlock.objects.get(
            user=self.reader,
            code=AchievementUnlock.Code.CORRESPONDENT_I,
        )
        self.assertEqual(first_degree.unlocked_at, articles[9].published_at)
        self.assertContains(response, "Корреспондент III степени")
        self.assertContains(response, "Корреспондент II степени")
        self.assertContains(response, "Корреспондент I степени")
        self.assertContains(response, "Использовано десятое письмо предъявителя.")

    def test_fiftieth_unique_read_awards_permanent_reader(self):
        views = []
        for index in range(50):
            article = self._published_article(f"Материал для чтения {index + 1}")
            views.append(ReaderArticleView.objects.create(user=self.reader, article=article))

        self.client.force_login(self.reader)
        response = self.client.get(reverse("reader-card"))

        mark = AchievementUnlock.objects.get(
            user=self.reader,
            code=AchievementUnlock.Code.PERMANENT_READER,
        )
        self.assertEqual(mark.unlocked_at, views[49].first_opened_at)
        self.assertContains(response, "Постоянный читатель")
        self.assertContains(response, "Прочитано пятьдесят материалов.")

    def test_anonymous_or_withheld_used_letter_awards_anonymous_source(self):
        article = self._published_article("Материал без раскрытия источника")
        EditorialLetter.objects.create(
            body="Подписанное письмо с просьбой о неразглашении",
            sender_name="Иван",
            anonymity_requested=True,
            sender_fingerprint=reader_fingerprint(self.reader),
            converted_article=article,
        )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        self.assertTrue(
            AchievementUnlock.objects.filter(
                user=self.reader,
                code=AchievementUnlock.Code.ANONYMOUS_SOURCE,
            ).exists()
        )
        self.assertContains(response, "Источник, пожелавший остаться неизвестным")

    def test_all_articles_from_completed_month_award_reader_without_gaps(self):
        today = timezone.localdate()
        current_month = today.replace(day=1)
        previous_month_last = current_month - timedelta(days=1)
        previous_month_first = previous_month_last.replace(day=1)
        for index in range(3):
            article = self._published_article(
                f"Материал прошлого месяца {index + 1}",
                published_at=timezone.make_aware(
                    datetime.combine(previous_month_first + timedelta(days=index), time.min)
                ),
            )
            ReaderArticleView.objects.create(user=self.reader, article=article)
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        self.assertTrue(
            AchievementUnlock.objects.filter(
                user=self.reader,
                code=AchievementUnlock.Code.COMPLETE_MONTH,
            ).exists()
        )
        self.assertContains(response, "Читатель без пропусков")

    def test_opening_three_month_old_material_awards_archive_reader(self):
        published_at = timezone.now() - timedelta(days=130)
        article = self._published_article("Материал из архива", published_at=published_at)
        ReaderArticleView.objects.create(
            user=self.reader,
            article=article,
            first_opened_at=timezone.now(),
            last_opened_at=timezone.now(),
        )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        self.assertTrue(
            AchievementUnlock.objects.filter(
                user=self.reader,
                code=AchievementUnlock.Code.ARCHIVE_READER,
            ).exists()
        )
        self.assertContains(response, "Читатель архива")

    def test_thirtieth_card_of_day_read_awards_rubric_subscriber(self):
        for index in range(30):
            article = self._published_article(
                f"Карта дня {index + 1}",
                rubric="Карта дня",
            )
            ReaderArticleView.objects.create(user=self.reader, article=article)
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        self.assertTrue(
            AchievementUnlock.objects.filter(
                user=self.reader,
                code=AchievementUnlock.Code.CARD_DAY_SUBSCRIBER,
            ).exists()
        )
        self.assertContains(response, "Постоянный подписчик рубрики")
        self.assertContains(response, "Прочитано тридцать выпусков рубрики")

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
        published = self._published_article("Старое письмо")
        EditorialLetter.objects.create(
            body="Историческое письмо без отпечатка",
            converted_article=published,
        )
        self.client.force_login(self.reader)

        response = self.client.get(reverse("reader-card"))

        self.assertFalse(AchievementUnlock.objects.filter(user=self.reader).exists())
        self.assertContains(response, "Пока без иных отметок. Редакция продолжает наблюдение.")
