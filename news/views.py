from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.db.models import Count, Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .auth import editor_required
from .editorial_service import create_or_update_draft_from_letter
from .forms import (
    ArticleForm,
    ArticleImageForm,
    EditorialLetterForm,
    InvitationAcceptForm,
    InvitationForm,
    MCPKeyForm,
    TarotDeckImportForm,
)
from .mcp_access import issue_mcp_key
from .models import Article, ArticleImage, EditorialLetter, Invitation, MCPAccessKey, TarotCard, TarotDraw
from .reader_activity import record_article_open, record_daily_visit
from .tarot_service import create_card_of_day, import_tarot_bundle, question_for_date, recent_draws


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


@login_required
def article_list(request):
    record_daily_visit(request.user)
    articles = Article.objects.filter(status=Article.Status.PUBLISHED, published_at__isnull=False)
    return render(request, "news/article_list.html", {"articles": articles})


@login_required
def article_detail(request, slug):
    article = get_object_or_404(
        Article,
        slug=slug,
        status=Article.Status.PUBLISHED,
        published_at__isnull=False,
    )
    record_article_open(request.user, article)
    return render(request, "news/article_detail.html", {"article": article})


@login_required
def article_image(request, pk):
    image = get_object_or_404(ArticleImage.objects.select_related("article"), pk=pk)
    article = image.article
    is_published = article.status == Article.Status.PUBLISHED and article.published_at is not None
    if not is_published and not request.user.is_staff:
        raise Http404

    try:
        handle = image.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404 from None

    response = FileResponse(handle, content_type=image.content_type)
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = f'inline; filename="{image.pk}"'
    return response


@login_required
def letter_create(request):
    if request.method == "POST":
        form = EditorialLetterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("letter-sent")
    else:
        form = EditorialLetterForm()

    return render(request, "news/letter_form.html", {"form": form})


@login_required
def letter_sent(request):
    return render(request, "news/letter_sent.html")


def invite_accept(request, token):
    if request.user.is_authenticated:
        messages.info(request, "Вы уже вошли во внутреннее издание.")
        return redirect("article-list")

    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_active:
        return render(request, "news/invite_accept.html", {"invitation": invitation, "invite_invalid": True}, status=410)

    if request.method == "POST":
        form = InvitationAcceptForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
                if not invitation.is_active:
                    return render(
                        request,
                        "news/invite_accept.html",
                        {"invitation": invitation, "invite_invalid": True},
                        status=410,
                    )
                user = form.save()
                invitation.accepted_at = timezone.now()
                invitation.accepted_by = user
                invitation.save(update_fields=["accepted_at", "accepted_by"])

            auth_login(request, user)
            messages.success(request, "Приглашение принято. Редакционная лента открыта.")
            return redirect("article-list")
    else:
        form = InvitationAcceptForm()

    return render(request, "news/invite_accept.html", {"form": form, "invitation": invitation})


@editor_required
def editor_dashboard(request):
    articles = Article.objects.annotate(
        unique_reader_count=Count("reader_views"),
        total_open_count=Sum("reader_views__open_count", default=0),
    )
    return render(request, "editor/dashboard.html", {"articles": articles})


@editor_required
def editor_tarot(request):
    today = timezone.localdate()
    import_form = TarotDeckImportForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "import":
            import_form = TarotDeckImportForm(request.POST, request.FILES)
            if import_form.is_valid():
                try:
                    count = import_tarot_bundle(import_form.cleaned_data["bundle"])
                except ValidationError as exc:
                    import_form.add_error("bundle", exc)
                else:
                    messages.success(request, f"Колода перенесена: {count} карт готовы к работе.")
                    return redirect("editor-tarot")
        elif action == "draw":
            try:
                draw, created = create_card_of_day(today)
            except ValidationError as exc:
                messages.error(request, exc.message)
            else:
                if created:
                    messages.success(request, "Карта дня вытянута. Черновик подготовлен редакции.")
                else:
                    messages.info(request, "На сегодня карта уже вытянута. Редакция придерживается первоначального прогноза.")
                if draw.article_id:
                    return redirect("editor-article-edit", pk=draw.article_id)
                return redirect("editor-tarot")

    today_draw = TarotDraw.objects.select_related("article").filter(draw_date=today).first()
    return render(
        request,
        "editor/tarot.html",
        {
            "import_form": import_form,
            "card_count": TarotCard.objects.count(),
            "today": today,
            "question": question_for_date(today),
            "today_draw": today_draw,
            "recent_draws": recent_draws(),
        },
    )


@editor_required
def editor_inbox(request):
    letters = EditorialLetter.objects.select_related("converted_article")
    return render(request, "editor/inbox.html", {"letters": letters})


@editor_required
def editor_invitations(request):
    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.created_by = request.user
            invitation.save()
            messages.success(request, "Приглашение подготовлено. Осталось передать ссылку адресату.")
            return redirect("editor-invitations")
    else:
        form = InvitationForm()

    invitations = list(Invitation.objects.select_related("created_by", "accepted_by"))
    for invitation in invitations:
        invitation.share_url = request.build_absolute_uri(invitation.get_absolute_url())

    return render(
        request,
        "editor/invitations.html",
        {"form": form, "invitations": invitations},
    )


@editor_required
@require_POST
def editor_invitation_revoke(request, pk):
    invitation = get_object_or_404(Invitation, pk=pk)
    if invitation.is_active:
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])
        messages.success(request, "Приглашение отозвано.")
    return redirect("editor-invitations")


@editor_required
def editor_integrations(request):
    raw_key = None
    if request.method == "POST":
        form = MCPKeyForm(request.POST)
        if form.is_valid():
            _, raw_key = issue_mcp_key(label=form.cleaned_data["label"], created_by=request.user)
            form = MCPKeyForm()
    else:
        form = MCPKeyForm()

    keys = MCPAccessKey.objects.select_related("created_by")
    mcp_url = request.build_absolute_uri("/mcp/")
    return render(
        request,
        "editor/integrations.html",
        {"form": form, "keys": keys, "raw_key": raw_key, "mcp_url": mcp_url},
    )


@editor_required
@require_POST
def editor_mcp_key_revoke(request, pk):
    access_key = get_object_or_404(MCPAccessKey, pk=pk)
    if access_key.is_active:
        access_key.revoked_at = timezone.now()
        access_key.save(update_fields=["revoked_at"])
        messages.success(request, f"Ключ «{access_key.label}» отозван.")
    return redirect("editor-integrations")


@editor_required
@require_POST
def editor_letter_review(request, pk):
    letter = get_object_or_404(EditorialLetter, pk=pk)
    if letter.status == EditorialLetter.Status.NEW:
        letter.status = EditorialLetter.Status.REVIEWED
        letter.reviewed_at = timezone.now()
        letter.save(update_fields=["status", "reviewed_at"])
    messages.success(request, "Письмо отмечено как просмотренное.")
    return redirect("editor-inbox")


@editor_required
@require_POST
def editor_letter_convert(request, pk):
    letter = get_object_or_404(EditorialLetter.objects.select_related("converted_article"), pk=pk)
    if letter.converted_article_id:
        article = letter.converted_article
    else:
        article = create_or_update_draft_from_letter(letter)

    messages.success(request, "Письмо превращено в черновик. Осталось сделать из слуха журналистику.")
    return redirect("editor-article-edit", pk=article.pk)


@editor_required
def editor_article_create(request):
    return _editor_article_form(request, Article())


@editor_required
def editor_article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)
    return _editor_article_form(request, article)


@editor_required
@require_POST
def editor_article_image_upload(request, pk):
    article = get_object_or_404(Article, pk=pk)
    form = ArticleImageForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

    image = form.save(commit=False)
    image.article = article
    image.save()
    return JsonResponse(
        {
            "id": str(image.pk),
            "marker": image.marker,
            "url": image.get_absolute_url(),
            "caption": image.caption,
            "layout": image.layout,
            "layout_label": image.get_layout_display(),
        },
        status=201,
    )


def _editor_article_form(request, article):
    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save(commit=False)
            action = request.POST.get("action", "save")

            if action == "preview":
                if article.published_at is None:
                    article.published_at = timezone.now()
                return render(request, "editor/article_preview.html", {"article": article})

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

    images = article.images.all() if article.pk else ()
    return render(
        request,
        "editor/article_form.html",
        {
            "form": form,
            "article": article,
            "image_form": ArticleImageForm(),
            "images": images,
        },
    )


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")
