from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from news.models import ReaderArticleView

from .service import set_daily_word


class WordlyReaderActivityTests(TestCase):
    def setUp(self):
        self.reader = get_user_model().objects.create_user(
            "wordly-reader-activity",
            password="secret",
        )
        self.daily_word, _ = set_daily_word(timezone.localdate(), "СЛУХИ")
        self.article = self.daily_word.article
        self.play_url = self.daily_word.get_absolute_url()
        self.client.force_login(self.reader)

    def test_direct_game_open_counts_as_reading_wordly_publication(self):
        response = self.client.get(self.play_url)

        self.assertEqual(response.status_code, 200)
        view = ReaderArticleView.objects.get(user=self.reader, article=self.article)
        self.assertEqual(view.open_count, 1)

    def test_wordly_game_render_does_not_inflate_open_count_on_every_attempt(self):
        self.client.get(self.play_url)
        self.client.get(self.play_url)
        self.client.post(self.play_url, {"guess": "ААААА"}, follow=True)

        view = ReaderArticleView.objects.get(user=self.reader, article=self.article)
        self.assertEqual(view.open_count, 1)

    def test_feed_entry_redirect_and_game_page_count_as_one_open(self):
        response = self.client.get(self.article.get_absolute_url(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], self.play_url)
        view = ReaderArticleView.objects.get(user=self.reader, article=self.article)
        self.assertEqual(view.open_count, 1)
