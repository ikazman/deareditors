from django import template
from django.utils import timezone

from canteen.models import DailyMenu


register = template.Library()


@register.inclusion_tag("canteen/_today_card.html")
def today_menu_card():
    menu = DailyMenu.objects.filter(
        menu_date=timezone.localdate(),
        is_published=True,
    ).first()
    return {"menu": menu}
