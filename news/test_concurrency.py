from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from news.article_images import save_article_image
from news.models import Article, ArticleImage, Invitation
from wordly.models import DailyWord, WordlyGame
from wordly.service import submit_guess


class InvitationTerminalStateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.editor = user_model.objects.create_user(
            "race-editor",
            password="secret",
            is_staff=True,
        )
        self.reader = user_model.objects.create_user("accepted-reader", password="secret")
        self.client.force_login(self.editor)

    def test_revoke_does_not_add_revoked_state_to_already_accepted_invitation(self):
        invitation = Invitation.objects.create(
            created_by=self.editor,
            accepted_at=timezone.now(),
            accepted_by=self.reader,
        )

        response = self.client.post(reverse("editor-invitation-revoke", args=[invitation.pk]))

        self.assertRedirects(response, reverse("editor-invitations"))
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertEqual(invitation.accepted_by, self.reader)
        self.assertIsNone(invitation.revoked_at)


class ArticleImageMarkerRaceTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(title="Гонка изображений", body="Текст")
        ArticleImage.objects.create(
            article=self.article,
            file="article-images/existing.png",
            alt_text="Первое изображение",
            content_type="image/png",
        )

    def test_marker_allocator_retries_after_stale_max_collision(self):
        image = ArticleImage(
            article=self.article,
            file="article-images/racing.png",
            alt_text="Второе изображение",
            content_type="image/png",
        )
        original_aggregate = QuerySet.aggregate
        stale_read_used = False

        def stale_first_image_max(queryset, *args, **kwargs):
            nonlocal stale_read_used
            if queryset.model is ArticleImage and not stale_read_used:
                stale_read_used = True
                return {"max_index": 0}
            return original_aggregate(queryset, *args, **kwargs)

        with patch.object(QuerySet, "aggregate", new=stale_first_image_max):
            save_article_image(image)

        self.assertTrue(stale_read_used)
        self.assertEqual(image.marker_index, 2)
        self.assertEqual(
            list(
                ArticleImage.objects.filter(article=self.article)
                .order_by("marker_index")
                .values_list("marker_index", flat=True)
            ),
            [1, 2],
        )


class WordlyAttemptRaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("wordly-race", password="secret")
        self.daily_word = DailyWord.objects.create(date=timezone.localdate(), word="КАССА")
        WordlyGame.objects.create(user=self.user, daily_word=self.daily_word)

    def test_losing_compare_and_swap_reloads_and_appends_to_newer_guesses(self):
        original_update = QuerySet.update
        simulated_competitor = False

        def concurrent_first_update(queryset, **kwargs):
            nonlocal simulated_competitor
            if (
                queryset.model is WordlyGame
                and "guesses" in kwargs
                and not simulated_competitor
            ):
                simulated_competitor = True
                original_update(
                    WordlyGame.objects.filter(user=self.user, daily_word=self.daily_word),
                    guesses=["ААААА"],
                    won=False,
                    completed_at=None,
                    updated_at=timezone.now(),
                )
                return 0
            return original_update(queryset, **kwargs)

        with patch.object(QuerySet, "update", new=concurrent_first_update):
            game = submit_guess(self.user, self.daily_word, "БББББ")

        self.assertTrue(simulated_competitor)
        self.assertEqual(game.guesses, ["ААААА", "БББББ"])
        self.assertFalse(game.won)
