from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("news", "0003_invitation"),
    ]

    operations = [
        migrations.CreateModel(
            name="MCPAccessKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120, verbose_name="название")),
                ("prefix", models.CharField(max_length=16, unique=True, verbose_name="префикс")),
                ("key_hash", models.CharField(editable=False, max_length=64, unique=True, verbose_name="хеш ключа")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="создано")),
                ("last_used_at", models.DateTimeField(blank=True, null=True, verbose_name="последнее использование")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="отозвано")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_mcp_keys",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="создал",
                    ),
                ),
            ],
            options={
                "verbose_name": "ключ MCP",
                "verbose_name_plural": "ключи MCP",
                "ordering": ["-created_at"],
            },
        ),
    ]
