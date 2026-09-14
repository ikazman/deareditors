from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from news.models import Article

from .models import DailyWord, WordlyGame
from .service import score_guess, set_daily_word, submit_guess, validate_letters


class WordlyScoringTests(SimpleTestCase):
    def test_duplicate_letters_are_consumed_only_once(self):
        self.assertEqual(
            score_guess("КАССА", "ААААА"),
            ["absent", "correct", "absent", "absent", "correct"],
        )

    def test_present_letter_respects_remaining_count(self):
        self.assertEqual(
            score_guess("КАССА", "САХАР"),
            ["present", "correct", "absent", "present", "absent"],
        )

    def test_any_five_russian_letters_are_valid_without_dictionary(self):
        self.assertEqual(validate_letters("ааааа"), "ААААА")

    def test_yo_is_normalized_to_editorial_e(self):
        self.assertEqual(validate_letters("ёлкае"), "ЕЛКАЕ")


class WordlyServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("reader", password="secret")
        self.today = timezone.localdate()
        self.daily_word = DailyWord.objects.create(date=self.today, word="КАССА")

    def test_guess_is_persisted_for_reader(self):
        game = submit_guess(self.user, self.daily_word, "ААААА")
        self.assertEqual(game.guesses, ["ААААА"])
        self.assertFalse(game.won)

        game = submit_guess(self.user, self.daily_word, "касса")
        self.assertEqual(game.guesses, ["ААААА", "КАССА"])
        self.assertTrue(game.won)
        self.assertIsNotNone(game.completed_at)

    def test_seventh_attempt_is_not_allowed(self):
        for guess in ["ААААА", "БББББ", "ВВВВВ", "ГГГГГ", "ДДДДД", "ЕЕЕЕЕ"]:
            submit_guess(self.user, self.daily_word, guess)

        with self.assertRaisesMessage(ValidationError, "Эта партия уже завершена."):
            submit_guess(self.user, self.daily_word, "КАССА")

    def test_editor_cannot_replace_word_after_first_attempt(self):
        submit_guess(self.user, self.daily_word, "ААААА")
        with self.assertRaisesMessage(ValidationError, "не может быть заменено"):
            set_daily_word(self.today, "СУДЬЯ")

    def test_editor_can_replace_word_before_any_attempt(self):
        word, changed = set_daily_word(self.today, "СУДЬЯ")
        self.assertTrue(changed)
        self.assertEqual(word.word, "СУДЬЯ")

    def test_setting_word_creates_publication_draft(self):
        target_date = self.today + timedelta(days=1)
        daily_word, changed = set_daily_word(target_date, "СУДЬЯ")

        self.assertTrue(changed)
        self.assertIsNotNone(daily_word.article_id)
        self.assertEqual(daily_word.article.title, "Редакция загадала слово")
        self.assertEqual(daily_word.article.rubric, "Вордли")
        self.assertEqual(daily_word.article.lead, "Пять букв. Шесть попыток.")
        self.assertEqual(daily_word.article.status, Article.Status.DRAFT)

    def test_published_word_cannot_be_replaced_even_before_first_guess(self):
        daily_word, _ = set_daily_word(self.today + timedelta(days=2), "СУДЬЯ")
        article = daily_word.article
        article.status = Article.Status.PUBLISHED
        article.save()

        with self.assertRaisesMessage(ValidationError, "не может быть заменено"):
            set_daily_word(daily_word.date, "КАССА")


class WordlyViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.reader = user_model.objects.create_user("reader-view", password="secret")
        self.editor = user_model.objects.create_user("editor-view", password="secret", is_staff=True)
        self.today = timezone.localdate()
        self.daily_word, _ = set_daily_word(self.today, "КАССА")
        self.article = self.daily_word.article
        self.article.status = Article.Status.PUBLISHED
        self.article.save()
        self.play_url = self.daily_word.get_absolute_url()

    def test_reader_archive_lists_published_word(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("wordly"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.today.strftime("%d.%m.%Y"))
        self.assertContains(response, "Редакция загадала слово")
        self.assertContains(response, "Сыграть")
        self.assertContains(response, self.play_url)

    def test_reader_page_shows_game_but_not_answer_before_finish(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.play_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пять букв. Шесть попыток")
        self.assertContains(response, "Редакция загадала слово")
        self.assertNotContains(response, "Словарь редакция не проверяет")
        self.assertNotContains(response, "Слово: КАССА")

    def test_reader_can_submit_nonword_letters(self):
        self.client.force_login(self.reader)
        response = self.client.post(self.play_url, {"guess": "ААААА"})
        self.assertRedirects(response, self.play_url)
        game = WordlyGame.objects.get(user=self.reader, daily_word=self.daily_word)
        self.assertEqual(game.guesses, ["ААААА"])

    def test_winning_guess_survives_reload(self):
        self.client.force_login(self.reader)
        self.client.post(self.play_url, {"guess": "КАССА"})
        response = self.client.get(self.play_url)
        self.assertContains(response, "Слово найдено")
        self.assertContains(response, "Попыток: 1")

    def test_reader_can_play_published_missed_day_from_archive(self):
        yesterday = self.today - timedelta(days=1)
        missed, _ = set_daily_word(yesterday, "СУДЬЯ")
        missed.article.status = Article.Status.PUBLISHED
        missed.article.save()

        self.client.force_login(self.reader)
        archive = self.client.get(reverse("wordly"))
        self.assertContains(archive, missed.get_absolute_url())

        response = self.client.post(missed.get_absolute_url(), {"guess": "СУДЬЯ"})
        self.assertRedirects(response, missed.get_absolute_url())
        self.assertTrue(WordlyGame.objects.get(user=self.reader, daily_word=missed).won)

    def test_unpublished_word_is_hidden_from_reader_but_available_to_editor(self):
        future_word, _ = set_daily_word(self.today + timedelta(days=1), "СУДЬЯ")

        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(future_word.get_absolute_url()).status_code, 404)

        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(future_word.get_absolute_url()).status_code, 200)

    def test_published_word_appears_in_feed_as_playable_rubric(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("article-list"))

        self.assertContains(response, "Вордли")
        self.assertContains(response, "Редакция загадала слово")
        self.assertContains(response, "Пять букв. Шесть попыток.")
        self.assertContains(response, ">Играть<")

        detail = self.client.get(self.article.get_absolute_url())
        self.assertRedirects(detail, self.play_url)

    def test_editor_can_set_future_word_manually_and_get_publication_draft(self):
        self.client.force_login(self.editor)
        target_date = self.today + timedelta(days=1)
        response = self.client.post(
            reverse("editor-wordly"),
            {"date": target_date.isoformat(), "word": "СУДЬЯ"},
        )
        daily_word = DailyWord.objects.get(date=target_date)

        self.assertRedirects(
            response,
            reverse("editor-article-edit", kwargs={"pk": daily_word.article_id}),
        )
        self.assertEqual(daily_word.word, "СУДЬЯ")
        self.assertEqual(daily_word.article.status, Article.Status.DRAFT)

    def test_reader_navigation_links_to_wordly_archive(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("article-list"))
        self.assertContains(response, f'href="{reverse("wordly")}"')
