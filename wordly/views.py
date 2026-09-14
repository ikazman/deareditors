from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from news.auth import editor_required

from .forms import DailyWordForm, GuessForm
from .models import DailyWord, WordlyGame
from .service import MAX_ATTEMPTS, board_rows, keyboard_states, set_daily_word, submit_guess


KEYBOARD_LAYOUT = (
    "ЙЦУКЕНГШЩЗХ",
    "ФЫВАПРОЛДЖЭ",
    "ЯЧСМИТЬБЮ",
)


def _keyboard(answer: str, guesses: list[str]):
    states = keyboard_states(answer, guesses)
    return [
        [{"letter": letter, "state": states.get(letter, "unused")} for letter in row]
        for row in KEYBOARD_LAYOUT
    ]


@login_required
def wordly(request):
    today = timezone.localdate()
    daily_word = DailyWord.objects.filter(date=today).first()
    game = None
    form = GuessForm()

    if daily_word:
        game = WordlyGame.objects.filter(user=request.user, daily_word=daily_word).first()

    if request.method == "POST":
        if not daily_word:
            messages.error(request, "Редакция еще не загадала слово на сегодня.")
            return redirect("wordly")

        form = GuessForm(request.POST)
        if form.is_valid():
            try:
                submit_guess(request.user, daily_word, form.cleaned_data["guess"])
            except ValidationError as exc:
                form.add_error("guess", exc.message)
            else:
                return redirect("wordly")

    guesses = list(game.guesses) if game else []
    finished = bool(game and (game.won or len(guesses) >= MAX_ATTEMPTS))
    context = {
        "today": today,
        "daily_word_exists": daily_word is not None,
        "form": form,
        "game": game,
        "guesses": guesses,
        "attempts_used": len(guesses),
        "max_attempts": MAX_ATTEMPTS,
        "finished": finished,
        "answer": daily_word.word if daily_word and finished else None,
        "board": board_rows(daily_word.word, guesses) if daily_word else [],
        "keyboard_rows": _keyboard(daily_word.word, guesses) if daily_word else [],
        "active_row": len(guesses) if daily_word and not finished else None,
    }
    return render(request, "wordly/game.html", context)


@editor_required
def editor_wordly(request):
    today = timezone.localdate()
    initial = {"date": today}
    today_word = DailyWord.objects.filter(date=today).first()
    if today_word:
        initial["word"] = today_word.word

    if request.method == "POST":
        form = DailyWordForm(request.POST)
        if form.is_valid():
            try:
                daily_word, changed = set_daily_word(
                    form.cleaned_data["date"],
                    form.cleaned_data["word"],
                )
            except ValidationError as exc:
                form.add_error("word", exc.message)
            else:
                if changed:
                    messages.success(request, f"Слово на {daily_word.date:%d.%m.%Y} установлено.")
                else:
                    messages.info(request, "Слово уже было установлено. Изменений нет.")
                return redirect("editor-wordly")
    else:
        form = DailyWordForm(initial=initial)

    words = (
        DailyWord.objects.annotate(game_count=Count("games"))
        .order_by("-date")[:14]
    )
    return render(
        request,
        "wordly/editor.html",
        {"form": form, "today": today, "today_word": today_word, "words": words},
    )
