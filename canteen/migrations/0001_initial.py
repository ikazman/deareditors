from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="DailyMenu",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("menu_date", models.DateField(unique=True, verbose_name="дата")),
                ("source_text", models.TextField(blank=True, verbose_name="исходный текст")),
                ("is_published", models.BooleanField(default=False, verbose_name="опубликовано")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="изменено")),
            ],
            options={"ordering": ["-menu_date"], "verbose_name": "меню дня", "verbose_name_plural": "меню дня"},
        ),
        migrations.CreateModel(
            name="MenuItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("first", "Первые блюда"), ("second", "Вторые блюда"), ("garnish", "Гарниры"), ("salad", "Салаты"), ("drink", "Напитки")], max_length=16, verbose_name="раздел")),
                ("name", models.CharField(max_length=180, verbose_name="блюдо")),
                ("price", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="цена")),
                ("portion", models.CharField(blank=True, max_length=80, verbose_name="выход")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="порядок")),
                ("menu", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="canteen.dailymenu", verbose_name="меню")),
            ],
            options={"ordering": ["sort_order", "id"], "verbose_name": "позиция меню", "verbose_name_plural": "позиции меню"},
        ),
        migrations.CreateModel(
            name="MenuSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="выбор сделан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="выбор изменен")),
                ("menu", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="selections", to="canteen.dailymenu", verbose_name="меню")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="canteen_selections", to=settings.AUTH_USER_MODEL, verbose_name="читатель")),
            ],
            options={"verbose_name": "выбор обеда", "verbose_name_plural": "выборы обеда"},
        ),
        migrations.CreateModel(
            name="MenuSelectionItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="selection_items", to="canteen.menuitem", verbose_name="позиция")),
                ("selection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="selected_items", to="canteen.menuselection", verbose_name="выбор")),
            ],
            options={"verbose_name": "выбранная позиция", "verbose_name_plural": "выбранные позиции"},
        ),
        migrations.AddConstraint(model_name="menuitem", constraint=models.UniqueConstraint(fields=("menu", "category", "name"), name="unique_canteen_item_per_menu")),
        migrations.AddConstraint(model_name="menuselection", constraint=models.UniqueConstraint(fields=("menu", "user"), name="unique_canteen_selection_per_reader")),
        migrations.AddConstraint(model_name="menuselectionitem", constraint=models.UniqueConstraint(fields=("selection", "item"), name="unique_canteen_item_in_selection")),
    ]
