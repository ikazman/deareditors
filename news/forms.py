from django import forms

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ("title", "lead", "body", "author_name")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Заголовок заметки", "autofocus": True}),
            "lead": forms.Textarea(attrs={"rows": 3, "placeholder": "Короткий лид — необязательно"}),
            "body": forms.Textarea(attrs={"rows": 16, "placeholder": "Текст заметки"}),
            "author_name": forms.TextInput(attrs={"placeholder": "Например: Дежурный редактор"}),
        }
