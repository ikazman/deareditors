from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from news.models import Article, EditorialLetter, ReaderArticleView, ReaderDailyVisit, ReaderProfile
from news.reader_identity import reader_fingerprint
from news.reader_marks import sync_reader_marks
from news.reader_profile import get_or_create_reader_profile


DEMO_USERNAME = "reader-demo"
DEMO_PASSWORD = "reader-demo-9182"
DEMO_PREFIX = "reader-demo-"


def aware_on(day, hour=10):
    return timezone.make_aware(datetime.combine(day, time(hour=hour)))


class Command(BaseCommand):
    help = "Создает локальный демонстрационный читательский билет со всей читательской историей."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=DEMO_USERNAME)
        parser.add_argument("--password", default=DEMO_PASSWORD)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_reader_demo предназначен только для локальной DEBUG-базы.")

        username = options["username"].strip()
        password = options["password"]
        if not username or not password:
            raise CommandError("Нужны непустые username и password.")

        User = get_user_model()
        reader, _ = User.objects.get_or_create(
            username=username,
            defaults={"first_name": "Анна", "email": "reader-demo@example.invalid"},
        )
        reader.first_name = "Анна"
        reader.is_staff = False
        reader.is_superuser = False
        reader.set_password(password)
        reader.save()

        profile = get_or_create_reader_profile(reader)
        issued_at = timezone.now() - timedelta(days=128)
        ReaderProfile.objects.filter(pk=profile.pk).update(issued_at=issued_at)
        profile.refresh_from_db()

        # Повторный запуск обновляет только собственные демонстрационные объекты.
        EditorialLetter.objects.filter(body__startswith="[reader-demo]").delete()
        ReaderArticleView.objects.filter(user=reader).delete()
        ReaderDailyVisit.objects.filter(user=reader).delete()
        reader.reader_marks.all().delete()

        today = timezone.localdate()
        first_of_this_month = today.replace(day=1)
        previous_month_last = first_of_this_month - timedelta(days=1)
        previous_month_first = previous_month_last.replace(day=1)

        articles = []

        # 30 выпусков «Карты дня» в завершенном месяце одновременно дают данные
        # для отметки подписчика рубрики и для проверки полного календарного месяца.
        for index in range(30):
            day = previous_month_first + timedelta(days=index % previous_month_last.day)
            published_at = aware_on(day, 8)
            article, _ = Article.objects.update_or_create(
                slug=f"{DEMO_PREFIX}card-{index + 1:02d}",
                defaults={
                    "title": f"Карта дня: демонстрационный выпуск {index + 1}",
                    "rubric": "Карта дня",
                    "lead": "Редакция располагает прогнозом на день.",
                    "body": "Демонстрационный материал читательской истории.",
                    "author_name": "Дорогая редакция",
                    "status": Article.Status.PUBLISHED,
                },
            )
            Article.objects.filter(pk=article.pk).update(published_at=published_at)
            article.refresh_from_db()
            articles.append(article)

        # Еще 20 обычных материалов. Первые десять считаются выросшими из писем
        # одного псевдонимного корреспондента.
        fingerprint = reader_fingerprint(reader)
        for index in range(20):
            if index == 0:
                day = today - timedelta(days=150)
            else:
                day = previous_month_first - timedelta(days=40 - index)
            published_at = aware_on(day, 11)
            article, _ = Article.objects.update_or_create(
                slug=f"{DEMO_PREFIX}article-{index + 1:02d}",
                defaults={
                    "title": f"Демонстрационное наблюдение № {index + 1}",
                    "lead": "Обстоятельства зафиксированы и переданы в архив редакции.",
                    "body": "До дорогой редакции дошел демонстрационный слух.",
                    "author_name": "Дорогая редакция",
                    "status": Article.Status.PUBLISHED,
                },
            )
            Article.objects.filter(pk=article.pk).update(published_at=published_at)
            article.refresh_from_db()
            articles.append(article)

            if index < 10:
                EditorialLetter.objects.create(
                    body=f"[reader-demo] Письмо корреспондента № {index + 1}",
                    sender_name="Анна" if index == 0 else "",
                    contact="",
                    anonymity_requested=index == 0,
                    sender_fingerprint=fingerprint,
                    status=EditorialLetter.Status.REVIEWED,
                    reviewed_at=published_at - timedelta(hours=2),
                    converted_article=article,
                )

        # Ровно 50 уникально прочитанных материалов. Повторные открытия у части
        # записей нужны, чтобы закрытая редакционная метрика тоже выглядела живой.
        ordered_articles = sorted(articles, key=lambda item: (item.published_at, item.pk))
        for index, article in enumerate(ordered_articles):
            if index == 0:
                # Старейший материал открыт сильно позже публикации: видна отметка архива.
                first_opened_at = timezone.now() - timedelta(days=10)
            else:
                first_opened_at = max(article.published_at + timedelta(hours=6), issued_at)
            ReaderArticleView.objects.update_or_create(
                user=reader,
                article=article,
                defaults={
                    "first_opened_at": first_opened_at,
                    "last_opened_at": first_opened_at + timedelta(hours=index % 4),
                    "open_count": 1 + (index % 3),
                },
            )

        # Посещения намеренно не образуют streak: это просто история присутствия.
        for days_ago in (0, 2, 5, 11, 24, 47, 83, 121):
            ReaderDailyVisit.objects.get_or_create(
                user=reader,
                visit_date=today - timedelta(days=days_ago),
            )

        marks = sync_reader_marks(reader)

        self.stdout.write(self.style.SUCCESS("Демонстрационный читатель готов."))
        self.stdout.write(f"Логин: {username}")
        self.stdout.write(f"Пароль: {password}")
        self.stdout.write(f"Билет: {profile.ticket_number}")
        self.stdout.write(f"Прочитано материалов: {ReaderArticleView.objects.filter(user=reader).count()}")
        self.stdout.write(f"Использовано писем: {EditorialLetter.objects.filter(sender_fingerprint=fingerprint).count()}")
        self.stdout.write(f"Отметок сейчас: {len(marks)}")
