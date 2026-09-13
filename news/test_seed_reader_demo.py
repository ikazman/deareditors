from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from .management.commands.seed_reader_demo import DEMO_PREFIX, DEMO_USERNAME
from .models import AchievementUnlock, Article, EditorialLetter, ReaderArticleView, ReaderProfile
from .reader_identity import reader_fingerprint


@override_settings(DEBUG=True)
class SeedReaderDemoTests(TestCase):
    def test_seed_creates_repeatable_reader_life_showcase(self):
        call_command("seed_reader_demo", verbosity=0)

        reader = get_user_model().objects.get(username=DEMO_USERNAME)
        fingerprint = reader_fingerprint(reader)
        self.assertTrue(reader.check_password("reader-demo-9182"))
        self.assertTrue(ReaderProfile.objects.filter(user=reader).exists())
        self.assertEqual(ReaderArticleView.objects.filter(user=reader).count(), 50)
        self.assertEqual(
            Article.objects.filter(slug__startswith=DEMO_PREFIX).count(),
            50,
        )
        self.assertEqual(
            EditorialLetter.objects.filter(sender_fingerprint=fingerprint).count(),
            10,
        )
        self.assertEqual(
            set(AchievementUnlock.objects.filter(user=reader).values_list("code", flat=True)),
            {
                AchievementUnlock.Code.CORRESPONDENT_III,
                AchievementUnlock.Code.CORRESPONDENT_II,
                AchievementUnlock.Code.CORRESPONDENT_I,
                AchievementUnlock.Code.PERMANENT_READER,
                AchievementUnlock.Code.ANONYMOUS_SOURCE,
                AchievementUnlock.Code.COMPLETE_MONTH,
                AchievementUnlock.Code.ARCHIVE_READER,
                AchievementUnlock.Code.CARD_DAY_SUBSCRIBER,
            },
        )

        call_command("seed_reader_demo", verbosity=0)

        self.assertEqual(ReaderArticleView.objects.filter(user=reader).count(), 50)
        self.assertEqual(Article.objects.filter(slug__startswith=DEMO_PREFIX).count(), 50)
        self.assertEqual(EditorialLetter.objects.filter(sender_fingerprint=fingerprint).count(), 10)
        self.assertEqual(AchievementUnlock.objects.filter(user=reader).count(), 8)
