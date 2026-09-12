import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class BootstrapEditorTests(TestCase):
    def run_bootstrap(self, *, username="", password="", email=""):
        env = {
            "DEAR_EDITORS_ADMIN_USERNAME": username,
            "DEAR_EDITORS_ADMIN_PASSWORD": password,
            "DEAR_EDITORS_ADMIN_EMAIL": email,
        }
        with patch.dict(os.environ, env, clear=False):
            call_command("bootstrap_editor", verbosity=0)

    def test_skips_when_credentials_are_not_configured(self):
        self.run_bootstrap()
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_creates_first_editor_from_environment(self):
        self.run_bootstrap(
            username="chief-editor",
            password="EditorialDesk!926",
            email="editor@example.test",
        )

        user = get_user_model().objects.get(username="chief-editor")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("EditorialDesk!926"))
        self.assertEqual(user.email, "editor@example.test")

    def test_existing_editor_is_not_changed_when_password_variable_is_removed(self):
        self.run_bootstrap(username="chief-editor", password="EditorialDesk!926")
        user = get_user_model().objects.get(username="chief-editor")
        password_hash = user.password

        self.run_bootstrap(username="chief-editor", password="")

        user.refresh_from_db()
        self.assertEqual(get_user_model().objects.filter(username="chief-editor").count(), 1)
        self.assertEqual(user.password, password_hash)
        self.assertTrue(user.check_password("EditorialDesk!926"))

    def test_refuses_to_elevate_existing_reader(self):
        get_user_model().objects.create_user(username="reader", password="ReaderPassword!926")

        with self.assertRaisesMessage(CommandError, "refusing to elevate"):
            self.run_bootstrap(username="reader", password="EditorialDesk!926")
