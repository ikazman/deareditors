from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import InvitationAcceptForm
from .invite_preview import (
    INVITE_PREVIEW_ALT,
    INVITE_PREVIEW_VERSION,
    invite_reference,
    invite_series,
    render_invite_preview,
)
from .models import Invitation
from .reader_profile import get_or_create_reader_profile


MONTHS_GENITIVE = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def _invite_status_label(invitation) -> str:
    if invitation.accepted_at is not None:
        return "Использовано"
    if invitation.revoked_at is not None:
        return "Отозвано"
    if invitation.expires_at <= timezone.now():
        return "Истекло"
    return "Не использовано"


def _prepare_invite_form(form):
    form.fields["username"].widget.attrs.pop("autofocus", None)
    for field_name in ("username", "password1", "password2"):
        form.fields[field_name].widget.attrs.pop("placeholder", None)
    return form


def _invite_description(invitation) -> str:
    expires = timezone.localtime(invitation.expires_at)
    return (
        f"Билет {invite_reference(invitation)}. "
        f"Действует до {expires.day} {MONTHS_GENITIVE[expires.month]}."
    )


def _invite_context(request, invitation, **extra):
    preview_path = reverse("invite-preview", kwargs={"token": invitation.token})
    preview_url = request.build_absolute_uri(
        f"{preview_path}?v={INVITE_PREVIEW_VERSION}"
    )
    context = {
        "invitation": invitation,
        "invite_reference": invite_reference(invitation),
        "invite_series": invite_series(invitation),
        "invite_status_label": _invite_status_label(invitation),
        "invite_url": request.build_absolute_uri(invitation.get_absolute_url()),
        "invite_preview_url": preview_url,
        "invite_preview_alt": INVITE_PREVIEW_ALT,
        "invite_description": _invite_description(invitation),
    }
    context.update(extra)
    return context


def invite_accept(request, token):
    if request.user.is_authenticated:
        messages.info(request, "Вы уже вошли во внутреннее издание.")
        return redirect("article-list")

    invitation = get_object_or_404(Invitation, token=token)
    if not invitation.is_active:
        return render(
            request,
            "news/invite_accept.html",
            _invite_context(request, invitation, invite_invalid=True),
            status=410,
        )

    if request.method == "POST":
        form = _prepare_invite_form(InvitationAcceptForm(request.POST))
        if form.is_valid():
            with transaction.atomic():
                invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
                if not invitation.is_active:
                    return render(
                        request,
                        "news/invite_accept.html",
                        _invite_context(request, invitation, invite_invalid=True),
                        status=410,
                    )
                user = form.save()
                invitation.accepted_at = timezone.now()
                invitation.accepted_by = user
                invitation.save(update_fields=["accepted_at", "accepted_by"])
                get_or_create_reader_profile(user)

            auth_login(request, user)
            messages.success(request, "Приглашение принято. Редакционная лента открыта.")
            return redirect("article-list")
    else:
        form = _prepare_invite_form(InvitationAcceptForm())

    return render(
        request,
        "news/invite_accept.html",
        _invite_context(request, invitation, form=form),
    )


def invite_preview(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if request.GET.get("v") != str(INVITE_PREVIEW_VERSION):
        raise Http404

    payload = render_invite_preview(invitation)
    response = HttpResponse(payload, content_type="image/png")
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    response["Content-Disposition"] = 'inline; filename="dear-editors-invite.png"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
