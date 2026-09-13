from pathlib import Path

from django.contrib.staticfiles import finders
from django.forms import Textarea
from django.test import SimpleTestCase

from .forms import ArticleImageForm


class ArticleImageEditorUITests(SimpleTestCase):
    def test_caption_starts_as_two_line_textarea(self):
        form = ArticleImageForm()
        widget = form.fields["caption"].widget

        self.assertIsInstance(widget, Textarea)
        self.assertEqual(widget.attrs["rows"], 2)
        self.assertIn("image-dialog__caption", widget.attrs["class"])

    def test_image_dialog_uses_fixed_shell_and_text_layout_choices(self):
        css_path = finders.find("news/article-images.css")
        self.assertIsNotNone(css_path)
        css = Path(css_path).read_text(encoding="utf-8")

        self.assertIn(".image-dialog__body", css)
        self.assertIn("overflow:auto", css)
        self.assertIn(".image-dialog__actions", css)
        self.assertIn(".image-dialog__choice input:checked+span", css)

    def test_image_upload_preserves_caret_before_dialog_focus_moves(self):
        js_path = finders.find("news/editor.js")
        self.assertIsNotNone(js_path)
        javascript = Path(js_path).read_text(encoding="utf-8")

        self.assertIn("pendingImageSelection = { ...savedSelection }", javascript)
        self.assertIn("insertImageMarker(payload.marker, insertionPoint)", javascript)
        self.assertIn("imageCaption?.addEventListener(\"input\", fitImageCaption)", javascript)
