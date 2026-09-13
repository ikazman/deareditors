from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class EditorAssetRegressionTests(SimpleTestCase):
    def _read_static(self, path):
        resolved = finders.find(path)
        self.assertIsNotNone(resolved)
        return Path(resolved).read_text(encoding="utf-8")

    def test_toolbar_keeps_textarea_focus_during_pointer_interaction(self):
        javascript = self._read_static("news/editor.js")

        self.assertIn('toolbar.addEventListener("pointerdown"', javascript)
        self.assertIn("event.preventDefault();", javascript)
        self.assertIn("preventScroll", javascript)

    def test_autogrow_does_not_remeasure_every_formatting_insertion(self):
        javascript = self._read_static("news/editor.js")

        self.assertIn("valueShrank", javascript)
        self.assertIn("contentOverflows", javascript)
