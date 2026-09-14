import hashlib
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import MCPAccessKey


KEY_PREFIX = "de_mcp"
KEY_ISSUE_ATTEMPTS = 8
LAST_USED_WRITE_INTERVAL = timedelta(minutes=5)


def _digest(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def issue_mcp_key(*, label: str, created_by=None) -> tuple[MCPAccessKey, str]:
    label = label.strip()
    if not label:
        raise ValueError("MCP key label must not be empty")

    # Do not use exists() -> create(): two workers could both observe a free
    # prefix. Let the database uniqueness constraints arbitrate the race and
    # retry inside a savepoint so an IntegrityError never poisons an outer
    # transaction.
    for _ in range(KEY_ISSUE_ATTEMPTS):
        prefix = secrets.token_hex(5)
        raw_key = f"{KEY_PREFIX}_{prefix}_{secrets.token_urlsafe(32)}"
        try:
            with transaction.atomic():
                access_key = MCPAccessKey.objects.create(
                    label=label,
                    prefix=prefix,
                    key_hash=_digest(raw_key),
                    created_by=created_by,
                )
        except IntegrityError:
            continue
        return access_key, raw_key

    raise RuntimeError("Не удалось выпустить уникальный MCP-ключ после повторных попыток.")


def authenticate_mcp_key(raw_key: str) -> MCPAccessKey | None:
    raw_key = (raw_key or "").strip()
    if not raw_key.startswith(f"{KEY_PREFIX}_"):
        return None

    access_key = MCPAccessKey.objects.filter(
        key_hash=_digest(raw_key),
        revoked_at__isnull=True,
    ).first()
    if access_key is None:
        return None

    now = timezone.now()
    if access_key.last_used_at is None or now - access_key.last_used_at >= LAST_USED_WRITE_INTERVAL:
        MCPAccessKey.objects.filter(pk=access_key.pk).update(last_used_at=now)
        access_key.last_used_at = now
    return access_key
