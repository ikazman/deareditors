from datetime import date
from decimal import Decimal

from django.db import migrations


SOURCE_TEXT = """МЕНЮ

Первые блюда:
- Куриный бульон с вермишелью — 96 руб. 300 мл.
- Рассольник — 103 руб. 300 мл.

Вторые блюда:
- Куриный шницель — 164 руб. 110/30 г.
- Котлеты рыбные — 144 руб. 110/30 г.
- Перец фаршированный — 167 руб. 220/30 г.
- Гуляш из свинины — 147 руб. 90/30 г.
- Биточки мясные — 141 руб. 100/30 г.

Гарниры:
- Греча — 65 руб. 140 г.
- Рис — 65 руб. 140 г.
- Пюре картофельное — 79 руб. 140 г.
- Рагу из кабачков — 91 руб. 140 г.

Салаты:
- Салат капустный — 64 руб. 110 г.
- Салат «Булгур» — 78 руб. 110 г.
- Салат «Оливье» — 78 руб. 140 г.
- Салат свекла с маслом — 79 руб. 110 г.
- Салат рыбный с рисом — 86 руб. 140 г.
- Салат из моркови — 65 руб. 110 г.

Напитки:
- Компот — 35 руб.
"""

ITEMS = [
    ("first", "Куриный бульон с вермишелью", "96", "300 мл."),
    ("first", "Рассольник", "103", "300 мл."),
    ("second", "Куриный шницель", "164", "110/30 г."),
    ("second", "Котлеты рыбные", "144", "110/30 г."),
    ("second", "Перец фаршированный", "167", "220/30 г."),
    ("second", "Гуляш из свинины", "147", "90/30 г."),
    ("second", "Биточки мясные", "141", "100/30 г."),
    ("garnish", "Греча", "65", "140 г."),
    ("garnish", "Рис", "65", "140 г."),
    ("garnish", "Пюре картофельное", "79", "140 г."),
    ("garnish", "Рагу из кабачков", "91", "140 г."),
    ("salad", "Салат капустный", "64", "110 г."),
    ("salad", "Салат «Булгур»", "78", "110 г."),
    ("salad", "Салат «Оливье»", "78", "140 г."),
    ("salad", "Салат свекла с маслом", "79", "110 г."),
    ("salad", "Салат рыбный с рисом", "86", "140 г."),
    ("salad", "Салат из моркови", "65", "110 г."),
    ("drink", "Компот", "35", ""),
]


def seed_menu(apps, schema_editor):
    DailyMenu = apps.get_model("canteen", "DailyMenu")
    MenuItem = apps.get_model("canteen", "MenuItem")
    menu, _ = DailyMenu.objects.update_or_create(
        menu_date=date(2026, 9, 15),
        defaults={"source_text": SOURCE_TEXT.strip(), "is_published": True},
    )
    MenuItem.objects.filter(menu=menu).delete()
    MenuItem.objects.bulk_create([
        MenuItem(
            menu=menu,
            category=category,
            name=name,
            price=Decimal(price),
            portion=portion,
            sort_order=index,
        )
        for index, (category, name, price, portion) in enumerate(ITEMS, start=1)
    ])


def unseed_menu(apps, schema_editor):
    DailyMenu = apps.get_model("canteen", "DailyMenu")
    DailyMenu.objects.filter(menu_date=date(2026, 9, 15)).delete()


class Migration(migrations.Migration):
    dependencies = [("canteen", "0001_initial")]
    operations = [migrations.RunPython(seed_menu, unseed_menu)]
