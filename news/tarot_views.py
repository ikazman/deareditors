from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auth import editor_required
from .models import TarotDraw
from .tarot_service import reroll_card_of_day


@editor_required
@require_POST
def editor_tarot_reroll(request):
    today = timezone.localdate()
    previous = (
        TarotDraw.objects.filter(draw_date=today)
        .values_list("card_name", "position")
        .first()
    )

    try:
        draw = reroll_card_of_day(today)
    except ValidationError as exc:
        messages.error(request, exc.message)
        return redirect("editor-tarot")

    if previous == (draw.card_name, draw.position):
        messages.info(
            request,
            "Редакция собрала и перемешала всю колоду заново. Карты настояли на прежнем ответе.",
        )
    else:
        messages.success(
            request,
            "Редакция собрала всю колоду, перемешала заново и вытянула новую карту.",
        )

    if draw.article_id:
        return redirect("editor-article-edit", pk=draw.article_id)
    return redirect("editor-tarot")
