from django.shortcuts import get_object_or_404, render

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
