from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class EditorNavigationTests(TestCase):
    def test_editor_shell_contains_desktop_and_mobile_navigation_labels(self):
        editor = get_user_model().objects.create_user(
            username="editor-nav",
            password="editor-nav-pass",
            is_staff=True,
        )
        self.client.force_login(editor)

        response = self.client.get(reverse("editor-dashboard"))

        self.assertContains(response, "Почта редакции")
        self.assertContains(response, ">Почта<")
        self.assertContains(response, "Интеграции")
        self.assertContains(response, ">ИИ<")
        self.assertContains(response, "Открыть издание")
        self.assertContains(response, ">Издание<")
        self.assertNotContains(response, "Открыть издание ↗")
        self.assertNotContains(response, 'target="_blank"')
