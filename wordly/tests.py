from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

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

        with self.assertRaisesMessage(ValidationError, "Сегодняшняя партия уже завершена."):
            submit_guess(self.user, self.daily_word, "КАССА")

    def test_editor_cannot_replace_word_after_first_attempt(self):
        submit_guess(self.user, self.daily_word, "ААААА")
        with self.assertRaisesMessage(ValidationError, "не может быть заменено"):
            set_daily_word(self.today, "СУДЬЯ")

    def test_editor_can_replace_word_before_any_attempt(self):
        word, changed = set_daily_word(self.today, "СУДЬЯ")
        self.assertTrue(changed)
        self.assertEqual(word.word, "СУДЬЯ")


class WordlyViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.reader = user_model.objects.create_user("reader-view", password="secret")
        self.editor = user_model.objects.create_user("editor-view", password="secret", is_staff=True)
        self.today = timezone.localdate()
        self.daily_word = DailyWord.objects.create(date=self.today, word="КАССА")

    def test_reader_page_shows_game_but_not_answer_before_finish(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("wordly"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пять букв. Шесть попыток")
        self.assertNotContains(response, "Слово: КАССА")

    def test_reader_can_submit_nonword_letters(self):
        self.client.force_login(self.reader)
        response = self.client.post(reverse("wordly"), {"guess": "ААААА"})
        self.assertRedirects(response, reverse("wordly"))
        game = WordlyGame.objects.get(user=self.reader, daily_word=self.daily_word)
        self.assertEqual(game.guesses, ["ААААА"])

    def test_winning_guess_survives_reload(self):
        self.client.force_login(self.reader)
        self.client.post(reverse("wordly"), {"guess": "КАССА"})
        response = self.client.get(reverse("wordly"))
        self.assertContains(response, "Слово найдено")
        self.assertContains(response, "Попыток: 1")

    def test_editor_can_set_future_word_manually(self):
        self.client.force_login(self.editor)
        target_date = self.today + timezone.timedelta(days=1)
        response = self.client.post(
            reverse("editor-wordly"),
            {"date": target_date.isoformat(), "word": "СУДЬЯ"},
        )
        self.assertRedirects(response, reverse("editor-wordly"))
        self.assertTrue(DailyWord.objects.filter(date=target_date, word="СУДЬЯ").exists())

    def test_reader_navigation_links_to_wordly(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("article-list"))
        self.assertContains(response, f'href="{reverse("wordly")}"')
