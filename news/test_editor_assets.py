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

    def test_autogrow_only_shrinks_after_deletion(self):
        javascript = self._read_static("news/editor.js")

        self.assertIn("valueShrank", javascript)
        self.assertIn("contentOverflows", javascript)
        self.assertIn("else if (valueShrank || deletion)", javascript)
        self.assertIn("shrinkToContent();", javascript)

    def test_draft_preview_is_fetched_without_leaving_editor_page(self):
        javascript = self._read_static("news/editor-preview.js")
        stylesheet = self._read_static("news/editor-preview.css")

        self.assertIn('event.submitter?.value !== "preview"', javascript)
        self.assertIn("event.preventDefault();", javascript)
        self.assertIn("new FormData(form)", javascript)
        self.assertIn("await fetch(", javascript)
        self.assertIn("frame.srcdoc", javascript)
        self.assertIn("draft-preview-dialog", stylesheet)
