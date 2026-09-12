import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import news.models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0002_editorialletter"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="токен")),
                ("label", models.CharField(blank=True, max_length=120, verbose_name="для кого")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="создано")),
                ("expires_at", models.DateTimeField(default=news.models.default_invite_expiry, verbose_name="действует до")),
                ("accepted_at", models.DateTimeField(blank=True, null=True, verbose_name="принято")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="отозвано")),
                (
                    "accepted_by",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="accepted_invitation",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="принял",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_invitations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="создал",
                    ),
                ),
            ],
            options={
                "verbose_name": "приглашение",
                "verbose_name_plural": "приглашения",
                "ordering": ["-created_at"],
            },
        ),
    ]
