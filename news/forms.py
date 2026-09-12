from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .editorial_service import normalize_article_body
from .models import Article, EditorialLetter, Invitation


class ReaderAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Имя для входа",
        widget=forms.TextInput(
            attrs={
                "class": "letter-input",
                "placeholder": "Имя для входа",
                "autofocus": True,
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "letter-input",
                "placeholder": "Пароль",
                "autocomplete": "current-password",
            }
        ),
    )


class InvitationAcceptForm(UserCreationForm):
    first_name = forms.CharField(
        label="Как к вам обращаться",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "letter-input",
                "placeholder": "Можно оставить пустым",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "letter-input",
                    "placeholder": "Имя для входа",
                    "autofocus": True,
                    "autocomplete": "username",
                }
            )
        }
        labels = {"username": "Имя для входа"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Пароль"
        self.fields["password2"].label = "Повторите пароль"
        self.fields["password1"].widget.attrs.update(
            {"class": "letter-input", "autocomplete": "new-password", "placeholder": "Пароль"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "letter-input", "autocomplete": "new-password", "placeholder": "Еще раз"}
        )


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ("label",)
        widgets = {
            "label": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Например: Мария из бухгалтерии",
                    "autofocus": True,
                }
            )
        }


class MCPKeyForm(forms.Form):
    label = forms.CharField(
        label="Название",
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Например: Perplexity",
                "autofocus": True,
            }
        ),
    )


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
        return normalize_article_body(self.cleaned_data["body"])


class EditorialLetterForm(forms.ModelForm):
    class Meta:
        model = EditorialLetter
        fields = ("body", "sender_name", "contact")
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "letter-textarea",
                    "rows": 7,
                    "placeholder": "До дорогой редакции дошел слух, что…",
                    "autofocus": True,
                }
            ),
            "sender_name": forms.TextInput(
                attrs={
                    "class": "letter-input",
                    "placeholder": "Можно не представляться",
                }
            ),
            "contact": forms.TextInput(
                attrs={
                    "class": "letter-input",
                    "placeholder": "Почта, Telegram или иной способ — если хотите ответа",
                }
            ),
        }
