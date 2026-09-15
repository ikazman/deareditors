from django.conf import settings
from django.db import models
from django.urls import reverse


class DailyMenu(models.Model):
    menu_date = models.DateField("дата", unique=True)
    source_text = models.TextField("исходный текст", blank=True)
    is_published = models.BooleanField("опубликовано", default=False)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)

    class Meta:
        ordering = ["-menu_date"]
        verbose_name = "меню дня"
        verbose_name_plural = "меню дня"

    def __str__(self):
        return f"Меню на {self.menu_date:%d.%m.%Y}"

    def get_absolute_url(self):
        return reverse("menu-detail", kwargs={"menu_date": self.menu_date.isoformat()})


class MenuItem(models.Model):
    class Category(models.TextChoices):
        FIRST = "first", "Первые блюда"
        SECOND = "second", "Вторые блюда"
        GARNISH = "garnish", "Гарниры"
        SALAD = "salad", "Салаты"
        DRINK = "drink", "Напитки"

    menu = models.ForeignKey(
        DailyMenu,
        verbose_name="меню",
        related_name="items",
        on_delete=models.CASCADE,
    )
    category = models.CharField("раздел", max_length=16, choices=Category.choices)
    name = models.CharField("блюдо", max_length=180)
    price = models.DecimalField("цена", max_digits=8, decimal_places=2)
    portion = models.CharField("выход", max_length=80, blank=True)
    sort_order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("menu", "category", "name"),
                name="unique_canteen_item_per_menu",
            )
        ]
        verbose_name = "позиция меню"
        verbose_name_plural = "позиции меню"

    def __str__(self):
        return f"{self.name} — {self.price} ₽"


class MenuSelection(models.Model):
    menu = models.ForeignKey(
        DailyMenu,
        verbose_name="меню",
        related_name="selections",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="читатель",
        related_name="canteen_selections",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField("выбор сделан", auto_now_add=True)
    updated_at = models.DateTimeField("выбор изменен", auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("menu", "user"),
                name="unique_canteen_selection_per_reader",
            )
        ]
        verbose_name = "выбор обеда"
        verbose_name_plural = "выборы обеда"

    def __str__(self):
        return f"{self.user} — {self.menu}"


class MenuSelectionItem(models.Model):
    selection = models.ForeignKey(
        MenuSelection,
        verbose_name="выбор",
        related_name="selected_items",
        on_delete=models.CASCADE,
    )
    item = models.ForeignKey(
        MenuItem,
        verbose_name="позиция",
        related_name="selection_items",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("selection", "item"),
                name="unique_canteen_item_in_selection",
            )
        ]
        verbose_name = "выбранная позиция"
        verbose_name_plural = "выбранные позиции"

    def __str__(self):
        return f"{self.selection}: {self.item}"
