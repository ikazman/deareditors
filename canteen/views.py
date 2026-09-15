from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from news.auth import editor_required
from news.reader_activity import record_daily_visit

from .forms import DailyMenuForm
from .models import DailyMenu, MenuItem, MenuSelection, MenuSelectionItem
from .service import save_menu_from_text


def _menu_groups(items):
    by_category = {value: [] for value, _label in MenuItem.Category.choices}
    for item in items:
        by_category[item.category].append(item)
    return [
        {"key": value, "label": label, "items": by_category[value]}
        for value, label in MenuItem.Category.choices
        if by_category[value]
    ]


@login_required
def menu_today(request):
    menu = DailyMenu.objects.filter(
        menu_date=timezone.localdate(),
        is_published=True,
    ).first()
    if menu is None:
        record_daily_visit(request.user)
        return render(request, "canteen/menu_missing.html")
    return redirect(menu.get_absolute_url())


@login_required
@require_http_methods(["GET", "POST"])
def menu_detail(request, menu_date):
    menu = get_object_or_404(DailyMenu, menu_date=menu_date, is_published=True)
    record_daily_visit(request.user)

    if request.method == "POST":
        requested_ids = request.POST.getlist("items")
        valid_ids = set(
            menu.items.filter(pk__in=requested_ids).values_list("pk", flat=True)
        )
        with transaction.atomic():
            selection, _ = MenuSelection.objects.select_for_update().get_or_create(
                menu=menu,
                user=request.user,
            )
            selection.selected_items.all().delete()
            MenuSelectionItem.objects.bulk_create(
                [MenuSelectionItem(selection=selection, item_id=item_id) for item_id in valid_ids]
            )
            selection.save(update_fields=["updated_at"])
        return redirect(menu.get_absolute_url())

    items = list(menu.items.annotate(choice_count=Count("selection_items")))
    selection = MenuSelection.objects.filter(menu=menu, user=request.user).first()
    selected_ids = set()
    if selection is not None:
        selected_ids = set(
            selection.selected_items.values_list("item_id", flat=True)
        )

    participant_count = menu.selections.count()
    selected_total = Decimal("0")
    for item in items:
        item.is_selected = item.pk in selected_ids
        item.choice_percent = (
            round(item.choice_count * 100 / participant_count)
            if participant_count
            else 0
        )
        if item.is_selected:
            selected_total += item.price

    return render(
        request,
        "canteen/menu_detail.html",
        {
            "menu": menu,
            "groups": _menu_groups(items),
            "has_selected": selection is not None,
            "participant_count": participant_count,
            "selected_total": selected_total,
        },
    )


@editor_required
def editor_menu(request):
    today = timezone.localdate()
    requested_date = request.GET.get("date")
    menu = None
    if requested_date:
        menu = DailyMenu.objects.filter(menu_date=requested_date).first()

    if request.method == "POST":
        form = DailyMenuForm(request.POST)
        if form.is_valid():
            try:
                menu = save_menu_from_text(
                    form.cleaned_data["menu_date"],
                    form.cleaned_data["source_text"],
                    publish=request.POST.get("action") == "publish",
                )
            except ValidationError as exc:
                form.add_error("source_text", exc)
            else:
                if menu.is_published:
                    messages.success(request, "Меню опубликовано. Столовая официально стала предметом редакционного учета.")
                else:
                    messages.success(request, "Меню сохранено как черновик.")
                return redirect(f"/editor/menu/?date={menu.menu_date.isoformat()}")
    else:
        if menu is None:
            menu = DailyMenu.objects.filter(menu_date=today).first()
        form = DailyMenuForm(
            initial={
                "menu_date": menu.menu_date if menu else today,
                "source_text": menu.source_text if menu else "",
            }
        )

    recent_menus = DailyMenu.objects.annotate(
        item_count=Count("items", distinct=True),
        participant_count=Count("selections", distinct=True),
    )[:14]
    return render(
        request,
        "canteen/editor_menu.html",
        {"form": form, "menu": menu, "recent_menus": recent_menus},
    )
