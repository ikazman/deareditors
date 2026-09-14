from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from news.auth import editor_required
from news.models import Article

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


def _published_for_readers(daily_word: DailyWord) -> bool:
    article = daily_word.article
    return bool(
        article
        and article.status == Article.Status.PUBLISHED
        and article.published_at is not None
        and article.published_at <= timezone.now()
        and daily_word.date <= timezone.localdate()
    )


def _game_context(request, daily_word: DailyWord, form: GuessForm | None = None) -> dict:
    game = WordlyGame.objects.filter(user=request.user, daily_word=daily_word).first()
    guesses = list(game.guesses) if game else []
    finished = bool(game and (game.won or len(guesses) >= MAX_ATTEMPTS))
    article = daily_word.article
    return {
        "daily_word": daily_word,
        "article": article,
        "form": form or GuessForm(),
        "game": game,
        "guesses": guesses,
        "attempts_used": len(guesses),
        "max_attempts": MAX_ATTEMPTS,
        "finished": finished,
        "answer": daily_word.word if finished else None,
        "board": board_rows(daily_word.word, guesses),
        "keyboard_rows": _keyboard(daily_word.word, guesses),
        "active_row": len(guesses) if not finished else None,
    }


@login_required
def wordly_archive(request):
    words = list(
        DailyWord.objects.select_related("article")
        .filter(
            date__lte=timezone.localdate(),
            article__status=Article.Status.PUBLISHED,
            article__published_at__isnull=False,
            article__published_at__lte=timezone.now(),
        )
        .order_by("-date")
    )
    games = {
        game.daily_word_id: game
        for game in WordlyGame.objects.filter(user=request.user, daily_word__in=words)
    }

    entries = []
    for daily_word in words:
        game = games.get(daily_word.pk)
        attempts = len(game.guesses) if game else 0
        if game and game.won:
            status = f"Угадано · {attempts}/6"
        elif game and attempts >= MAX_ATTEMPTS:
            status = "Не угадано"
        elif game:
            status = f"Продолжить · {attempts}/6"
        else:
            status = "Сыграть"
        entries.append({"daily_word": daily_word, "game": game, "status": status})

    return render(request, "wordly/archive.html", {"entries": entries})


@login_required
def wordly_play(request, year: int, month: int, day: int):
    try:
        target_date = date(year, month, day)
    except ValueError:
        raise Http404 from None

    daily_word = get_object_or_404(
        DailyWord.objects.select_related("article"),
        date=target_date,
    )
    if not request.user.is_staff and not _published_for_readers(daily_word):
        raise Http404

    form = GuessForm()
    if request.method == "POST":
        form = GuessForm(request.POST)
        if form.is_valid():
            try:
                submit_guess(request.user, daily_word, form.cleaned_data["guess"])
            except ValidationError as exc:
                form.add_error("guess", exc.message)
            else:
                return redirect("wordly-play", year=year, month=month, day=day)

    return render(request, "wordly/game.html", _game_context(request, daily_word, form))


@editor_required
def editor_wordly(request):
    today = timezone.localdate()
    initial = {"date": today}
    today_word = DailyWord.objects.select_related("article").filter(date=today).first()
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
                    if daily_word.article.published_at <= timezone.now():
                        messages.success(
                            request,
                            f"Слово на {daily_word.date:%d.%m.%Y} установлено и опубликовано в ленте.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Слово на {daily_word.date:%d.%m.%Y} установлено. Выпуск появится в ленте в этот день.",
                        )
                else:
                    messages.info(request, "Слово уже было установлено. Изменений нет.")
                return redirect("editor-wordly")
    else:
        form = DailyWordForm(initial=initial)

    words = list(
        DailyWord.objects.select_related("article")
        .prefetch_related("games")
        .order_by("-date")[:14]
    )
    word_rows = []
    for daily_word in words:
        games = list(daily_word.games.all())
        winners = [game for game in games if game.won]
        average_attempts = (
            sum(len(game.guesses) for game in winners) / len(winners)
            if winners
            else None
        )
        word_rows.append(
            {
                "daily_word": daily_word,
                "game_count": len(games),
                "win_count": len(winners),
                "average_attempts": average_attempts,
            }
        )

    return render(
        request,
        "wordly/editor.html",
        {
            "form": form,
            "today": today,
            "today_word": today_word,
            "word_rows": word_rows,
        },
    )
