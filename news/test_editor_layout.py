from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase

from .forms import ArticleForm


class ArticleEditorLayoutTests(SimpleTestCase):
    def test_article_textareas_start_compact(self):
        form = ArticleForm()

        self.assertEqual(form.fields["title"].widget.attrs["rows"], 1)
        self.assertEqual(form.fields["lead"].widget.attrs["rows"], 2)
        self.assertEqual(form.fields["body"].widget.attrs["rows"], 5)

    def test_mobile_toolbar_becomes_right_side_rail_and_removes_large_min_heights(self):
        css_path = finders.find("news/editor-toolbar.css")
        self.assertIsNotNone(css_path)
        css = Path(css_path).read_text(encoding="utf-8")

        self.assertIn("@media (max-width:40rem)", css)
        self.assertIn(".textarea--lead,.textarea--body{min-height:0}", css)
        self.assertIn(".field--body:focus-within .editor-toolbar", css)
        self.assertIn("position:fixed", css)
        self.assertIn("right:max(.45rem, env(safe-area-inset-right))", css)
        self.assertIn("flex-direction:column", css)
        self.assertIn("background:var(--paper)", css)

    def test_mobile_toolbar_uses_compact_icons_while_desktop_keeps_labels(self):
        template = (Path(settings.BASE_DIR) / "templates" / "editor" / "article_form.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('class="field field--body"', template)
        self.assertIn('class="editor-tool__label">• список</span>', template)
        self.assertIn('class="editor-tool__mobile editor-tool__icon"', template)
        self.assertIn('aria-label="Маркированный список"', template)
        self.assertIn('aria-label="Нумерованный список"', template)
        self.assertIn('aria-label="Ссылка"', template)

    def test_editor_autogrow_can_recalculate_downward(self):
        js_path = finders.find("news/editor.js")
        self.assertIsNotNone(js_path)
        javascript = Path(js_path).read_text(encoding="utf-8")

        self.assertIn('textarea.style.height = "auto"', javascript)
        self.assertIn("Math.max(manualFloor, textarea.scrollHeight)", javascript)
        self.assertIn("ResizeObserver", javascript)
