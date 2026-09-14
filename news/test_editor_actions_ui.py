from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class EditorActionsUITests(SimpleTestCase):
    def test_published_actions_have_main_and_destructive_groups(self):
        template = (settings.BASE_DIR / "templates/editor/article_form.html").read_text(encoding="utf-8")

        main_group = template.index('class="actions__main"')
        danger_group = template.index('class="actions__danger"')
        self.assertLess(main_group, danger_group)
        self.assertIn('value="save_preview"', template)
        self.assertIn("Посмотреть черновик", template)
        self.assertNotIn("Посмотреть черновик ↗", template)
        self.assertNotIn('formtarget="_blank"', template)
        self.assertIn("Открыть в издании", template)
        self.assertNotIn("Открыть в издании ↗", template)
        self.assertIn("Снять с публикации", template)

    def test_desktop_and_mobile_spacing_express_grouping(self):
        css_path = finders.find("news/editor-actions.css")
        self.assertIsNotNone(css_path)
        css = Path(css_path).read_text(encoding="utf-8")

        self.assertIn("justify-content:space-between", css)
        self.assertIn(".actions__main", css)
        self.assertIn(".actions__danger", css)
        self.assertIn("margin-top:1.35rem", css)
