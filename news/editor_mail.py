from django.db.models import Count, Max
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .auth import editor_required
from .models import EditorialLetter


@editor_required
@require_GET
def editor_mail_status(request):
    stats = EditorialLetter.objects.filter(status=EditorialLetter.Status.NEW).aggregate(
        new_count=Count("id"),
        latest_id=Max("id"),
    )
    response = JsonResponse(
        {
            "new_count": stats["new_count"],
            "latest_id": stats["latest_id"],
        }
    )
    response["Cache-Control"] = "private, no-store"
    return response
