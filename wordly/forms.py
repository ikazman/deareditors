from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .service import validate_letters


class DailyWordForm(forms.Form):
    date = forms.DateField(
        label="Дата",
        widget=forms.DateInput(attrs={"type": "date", "class": "input"}),
        initial=timezone.localdate,
    )
    word = forms.CharField(
        label="Слово",
        min_length=5,
        max_length=5,
        widget=forms.TextInput(
            attrs={
                "class": "input input--display",
                "maxlength": "5",
                "autocomplete": "off",
                "spellcheck": "false",
                "placeholder": "Пять букв",
            }
        ),
    )

    def clean_word(self):
        try:
            return validate_letters(self.cleaned_data["word"])
        except ValidationError as exc:
            raise forms.ValidationError(exc.message) from exc


class GuessForm(forms.Form):
    guess = forms.CharField(min_length=5, max_length=5)

    def clean_guess(self):
        try:
            return validate_letters(self.cleaned_data["guess"])
        except ValidationError as exc:
            raise forms.ValidationError(exc.message) from exc
