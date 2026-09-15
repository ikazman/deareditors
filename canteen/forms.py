from django import forms


class DailyMenuForm(forms.Form):
    menu_date = forms.DateField(
        label="Дата меню",
        widget=forms.DateInput(attrs={"class": "input", "type": "date"}),
    )
    source_text = forms.CharField(
        label="Меню",
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea--body",
                "rows": 20,
                "placeholder": "Вставьте меню целиком — с разделами, ценами и выходом блюд.",
            }
        ),
    )
