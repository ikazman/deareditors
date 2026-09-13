from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Article, Invitation, ReaderDailyVisit, ReaderProfile
from .reader_profile import get_or_create_reader_profile


class ReaderCardTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.reader = self.user_model.objects.create_user(
            username="reader-card",
            password="reader-card-pass-9182",
            first_name="Анна",
        )

    def test_reader_card_requires_login(self):
        response = self.client.get(reverse("reader-card"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_reader_card_issues_stable_human_readable_number(self):
        self.client.force_login(self.reader)

        first = self.client.get(reverse("reader-card"))
        profile = ReaderProfile.objects.get(user=self.reader)
        second = self.client.get(reverse("reader-card"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertRegex(profile.ticket_number, r"^DE-\d{2}-\d{4}$")
        self.assertContains(first, profile.ticket_number)
        self.assertContains(first, "Анна")
        self.assertEqual(ReaderProfile.objects.filter(user=self.reader).count(), 1)
        self.assertEqual(
            ReaderProfile.objects.get(user=self.reader).ticket_number,
            profile.ticket_number,
        )

    def test_reader_card_shows_reading_stats(self):
        first_article = Article.objects.create(
            title="Первый материал",
            body="Редакция фиксирует чтение.",
            status=Article.Status.PUBLISHED,
        )
        second_article = Article.objects.create(
            title="Второй материал",
            body="Повторное наблюдение.",
            status=Article.Status.PUBLISHED,
        )
        self.client.force_login(self.reader)
        self.client.get(first_article.get_absolute_url())
        self.client.get(first_article.get_absolute_url())
        self.client.get(second_article.get_absolute_url())
        ReaderDailyVisit.objects.get_or_create(
            user=self.reader,
            visit_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get(reverse("reader-card"))

        self.assertEqual(response.context["articles_read"], 2)
        self.assertEqual(response.context["days_visited"], 2)

    def test_accepting_invitation_issues_reader_profile(self):
        invitation = Invitation.objects.create(label="Новый читатель")

        response = self.client.post(
            invitation.get_absolute_url(),
            {
                "username": "invited-reader",
                "first_name": "Ирина",
                "password1": "MosaicRiver!9182",
                "password2": "MosaicRiver!9182",
            },
        )

        self.assertRedirects(response, reverse("article-list"))
        invited = self.user_model.objects.get(username="invited-reader")
        self.assertTrue(ReaderProfile.objects.filter(user=invited).exists())

    def test_ticket_number_collision_is_retried(self):
        other_reader = self.user_model.objects.create_user(
            username="other-reader-card",
            password="other-reader-card-pass-9182",
        )
        ReaderProfile.objects.create(
            user=self.reader,
            ticket_number="DE-01-0002",
        )

        with patch(
            "news.reader_profile.secrets.randbelow",
            side_effect=[1, 2, 3, 4],
        ):
            profile = get_or_create_reader_profile(other_reader)

        self.assertEqual(profile.ticket_number, "DE-03-0004")
