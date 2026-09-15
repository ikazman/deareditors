from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import WordlyGame
from .service import set_daily_word


class WordlyAjaxTests(TestCase):
    def setUp(self):
        self.reader = get_user_model().objects.create_user("wordly-ajax-reader", password="secret")
        self.daily_word, _ = set_daily_word(timezone.localdate(), "КАССА")
        self.play_url = self.daily_word.get_absolute_url()
        self.client.force_login(self.reader)

    def ajax_post(self, guess):
        return self.client.post(
            self.play_url,
            {"guess": guess},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

    def test_ajax_guess_updates_game_without_redirect(self):
        response = self.ajax_post("ААААА")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response.headers)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("wordly-board", payload["html"])
        self.assertIn("data-active-cell", payload["html"])

        game = WordlyGame.objects.get(user=self.reader, daily_word=self.daily_word)
        self.assertEqual(game.guesses, ["ААААА"])
        self.assertFalse(game.won)

    def test_ajax_winning_guess_returns_finished_state(self):
        response = self.ajax_post("КАССА")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("Слово найдено", payload["html"])
        self.assertNotIn('aria-label="Клавиатура"', payload["html"])

        game = WordlyGame.objects.get(user=self.reader, daily_word=self.daily_word)
        self.assertTrue(game.won)

    def test_ajax_invalid_guess_returns_inline_error(self):
        response = self.ajax_post("АААА")

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("wordly-errors", payload["html"])
        self.assertFalse(WordlyGame.objects.filter(user=self.reader, daily_word=self.daily_word).exists())
