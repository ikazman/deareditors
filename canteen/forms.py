from django import forms


class DailyMenuForm(forms.Form):
    menu_date = forms.DateField(
        label="Дата меню",
        widget=forms.DateInput(attrs={"class": "input", "type": "date"}),
    )
    title = forms.CharField(
        label="Заголовок",
        required=False,
        max_length=220,
        widget=forms.TextInput(
            attrs={
                "class": "input input--display",
                "placeholder": "Меню столовой на сегодня",
            }
        ),
    )
    lead = forms.CharField(
        label="Лид",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea--lead",
                "rows": 3,
                "placeholder": "Короткая фраза для ленты и страницы меню.",
            }
        ),
    )
    source_text = forms.CharField(
        label="Исходное меню",
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea--body",
                "rows": 14,
                "placeholder": "Вставьте меню целиком — с разделами, ценами и выходом блюд.",
            }
        ),
    )
