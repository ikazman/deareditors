from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ArticleForm
from .models import Article


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


@login_required
def editor_dashboard(request):
    articles = Article.objects.all()
    return render(request, "editor/dashboard.html", {"articles": articles})


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
