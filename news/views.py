from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, connection, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ArticleForm, EditorialLetterForm
from .models import Article, EditorialLetter


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


def article_list(request):
    articles = Article.objects.filter(status=Article.Status.PUBLISHED, published_at__isnull=False)
    return render(request, "news/article_list.html", {"articles": articles})


def article_detail(request, slug):
    article = get_object_or_404(
        Article,
        slug=slug,
        status=Article.Status.PUBLISHED,
        published_at__isnull=False,
    )
    return render(request, "news/article_detail.html", {"article": article})


def letter_create(request):
    if request.method == "POST":
        form = EditorialLetterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("letter-sent")
    else:
        form = EditorialLetterForm()

    return render(request, "news/letter_form.html", {"form": form})


def letter_sent(request):
    return render(request, "news/letter_sent.html")


@login_required
def editor_dashboard(request):
    articles = Article.objects.all()
    return render(request, "editor/dashboard.html", {"articles": articles})


@login_required
def editor_inbox(request):
    letters = EditorialLetter.objects.select_related("converted_article")
    return render(request, "editor/inbox.html", {"letters": letters})


@login_required
@require_POST
def editor_letter_review(request, pk):
    letter = get_object_or_404(EditorialLetter, pk=pk)
    if letter.status == EditorialLetter.Status.NEW:
        letter.status = EditorialLetter.Status.REVIEWED
        letter.reviewed_at = timezone.now()
        letter.save(update_fields=["status", "reviewed_at"])
    messages.success(request, "Письмо отмечено как просмотренное.")
    return redirect("editor-inbox")


@login_required
@require_POST
def editor_letter_convert(request, pk):
    with transaction.atomic():
        letter = get_object_or_404(EditorialLetter.objects.select_for_update(), pk=pk)

        if letter.converted_article_id:
            article = letter.converted_article
        else:
            article = Article.objects.create(
                title="До редакции дошел новый слух",
                body=letter.body,
                author_name="Дорогая редакция",
                status=Article.Status.DRAFT,
            )
            letter.status = EditorialLetter.Status.REVIEWED
            letter.reviewed_at = timezone.now()
            letter.converted_article = article
            letter.save(update_fields=["status", "reviewed_at", "converted_article"])

    messages.success(request, "Письмо превращено в черновик. Осталось сделать из слуха журналистику.")
    return redirect("editor-article-edit", pk=article.pk)


@login_required
def editor_article_create(request):
    return _editor_article_form(request, Article())


@login_required
def editor_article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return _editor_article_form(request, article)


def _editor_article_form(request, article):
    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save(commit=False)
            action = request.POST.get("action", "save")

            if action == "publish":
                article.status = Article.Status.PUBLISHED
            elif action == "draft":
                article.status = Article.Status.DRAFT

            article.save()

            if article.status == Article.Status.PUBLISHED:
                messages.success(request, "Материал опубликован.")
            else:
                messages.success(request, "Черновик сохранен.")
            return redirect("editor-dashboard")
    else:
        form = ArticleForm(instance=article)

    return render(request, "editor/article_form.html", {"form": form, "article": article})


@login_required
@require_POST
def editor_logout(request):
    logout(request)
    return redirect("article-list")
