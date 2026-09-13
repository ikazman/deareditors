import zipfile

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .editorial_service import normalize_article_body
from .models import Article, ArticleImage, EditorialLetter, Invitation


MAX_ARTICLE_IMAGE_SIZE = 12 * 1024 * 1024
MAX_TAROT_BUNDLE_SIZE = 25 * 1024 * 1024


def detect_image_content_type(upload):
    header = upload.read(16)
    upload.seek(0)

    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


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
                    "rows": 1,
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
                    "rows": 5,
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


class ArticleImageForm(forms.ModelForm):
    class Meta:
        model = ArticleImage
        fields = ("file", "caption", "alt_text", "layout")
        widgets = {
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "image-dialog__file",
                    "accept": "image/jpeg,image/png,image/webp,image/gif",
                }
            ),
            "caption": forms.Textarea(
                attrs={
                    "class": "image-dialog__input image-dialog__caption",
                    "rows": 2,
                    "placeholder": "Например: Фото предоставлено источником, пожелавшим остаться в столовой",
                }
            ),
            "alt_text": forms.TextInput(
                attrs={
                    "class": "image-dialog__input",
                    "placeholder": "Коротко опишите, что изображено",
                }
            ),
            "layout": forms.RadioSelect(attrs={"class": "image-dialog__radio"}),
        }

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > MAX_ARTICLE_IMAGE_SIZE:
            raise forms.ValidationError("Файл слишком большой. Максимум — 12 МБ.")

        content_type = detect_image_content_type(upload)
        if content_type is None:
            raise forms.ValidationError("Редакция принимает JPEG, PNG, WebP и GIF.")

        self.instance.content_type = content_type
        return upload


class TarotDeckImportForm(forms.Form):
    bundle = forms.FileField(
        label="Архив старой колоды",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "tarot-import__file",
                "accept": ".zip,application/zip",
            }
        ),
    )

    def clean_bundle(self):
        upload = self.cleaned_data["bundle"]
        if upload.size > MAX_TAROT_BUNDLE_SIZE:
            raise forms.ValidationError("Архив слишком большой. Максимум — 25 МБ.")
        try:
            with zipfile.ZipFile(upload) as archive:
                archive.testzip()
        except (zipfile.BadZipFile, OSError):
            raise forms.ValidationError("Нужен обычный ZIP-архив репозитория tarot-hb.") from None
        finally:
            upload.seek(0)
        return upload


class EditorialLetterForm(forms.ModelForm):
    class Meta:
        model = EditorialLetter
        fields = ("body", "sender_name", "contact", "anonymity_requested")
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
            "anonymity_requested": forms.CheckboxInput(attrs={"class": "letter-checkbox"}),
        }
