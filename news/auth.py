from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def editor_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Редакционный стол доступен только редакции.")
            return redirect("article-list")
        return view_func(request, *args, **kwargs)

    return wrapped
