from django import forms

from .models import Article


SIGNOFF = "Будем наблюдать."


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ("title", "lead", "body", "author_name")
        widgets = {
            "title": forms.Textarea(
                attrs={
                    "class": "textarea input--display",
                    "rows": 2,
                    "placeholder": "О чем дошел слух",
                    "autofocus": True,
                }
            ),
            "lead": forms.Textarea(
                attrs={
                    "class": "textarea textarea--lead",
                    "rows": 2,
                    "placeholder": "Одна фраза, которая делает всю работу",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "textarea textarea--body",
                    "rows": 12,
                    "placeholder": "До дорогой редакции дошел слух, что…",
                }
            ),
            "author_name": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Например: Дежурный редактор",
                }
            ),
        }

    def clean_body(self):
        body = self.cleaned_data["body"].rstrip()
        lines = body.splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and lines[-1].strip().casefold() == SIGNOFF.casefold():
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
        return "\n".join(lines).rstrip()
