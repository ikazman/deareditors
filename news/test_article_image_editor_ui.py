from pathlib import Path

from django.conf import settings
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

    def test_article_images_do_not_expand_tall_artwork_to_full_measure(self):
        css_path = finders.find("news/article-images.css")
        self.assertIsNotNone(css_path)
        css = Path(css_path).read_text(encoding="utf-8")

        self.assertIn("width:auto", css)
        self.assertIn("max-width:100%", css)
        self.assertIn("max-height:min(42rem,72vh)", css)
        self.assertIn("max-height:62vh", css)
        self.assertIn("object-fit:contain", css)

    def test_image_upload_preserves_caret_before_dialog_focus_moves(self):
        js_path = finders.find("news/editor.js")
        self.assertIsNotNone(js_path)
        javascript = Path(js_path).read_text(encoding="utf-8")

        self.assertIn("pendingImageSelection = { ...savedSelection }", javascript)
        self.assertIn("insertImageMarker(payload.marker, insertionPoint)", javascript)
        self.assertIn("imageCaption?.addEventListener(\"input\", fitImageCaption)", javascript)

    def test_editor_actions_are_named_and_visually_grouped(self):
        template = (Path(settings.BASE_DIR) / "templates" / "editor" / "article_form.html").read_text(encoding="utf-8")
        css_path = finders.find("news/editor-actions.css")
        self.assertIsNotNone(css_path)
        css = Path(css_path).read_text(encoding="utf-8")

        self.assertIn('value="save_preview"', template)
        self.assertIn("Посмотреть черновик", template)
        self.assertNotIn("Посмотреть черновик ↗", template)
        self.assertNotIn('formtarget="_blank"', template)
        self.assertIn("Открыть в издании", template)
        self.assertNotIn("Открыть в издании ↗", template)
        self.assertIn('class="actions__main"', template)
        self.assertIn('class="actions__danger"', template)
        self.assertIn("justify-content:space-between", css)
        self.assertIn("margin-top:1.35rem", css)
