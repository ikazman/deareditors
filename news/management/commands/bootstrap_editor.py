import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the first Dear Editors superuser from environment variables, once."

    def handle(self, *args, **options):
        username = os.environ.get("DEAR_EDITORS_ADMIN_USERNAME", "").strip()
        password = os.environ.get("DEAR_EDITORS_ADMIN_PASSWORD", "")
        email = os.environ.get("DEAR_EDITORS_ADMIN_EMAIL", "").strip()

        if not username and not password:
            self.stdout.write("Editor bootstrap skipped: credentials are not configured.")
            return

        if not username or not password:
            raise CommandError(
                "DEAR_EDITORS_ADMIN_USERNAME and DEAR_EDITORS_ADMIN_PASSWORD must be set together."
            )

        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing:
            if not existing.is_staff or not existing.is_superuser:
                raise CommandError(
                    f"User {username!r} already exists but is not an editor/superuser; refusing to elevate it automatically."
                )
            self.stdout.write(f"Editor {username!r} already exists; bootstrap skipped.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Editor {username!r} created."))
