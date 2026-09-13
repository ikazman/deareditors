from django.utils.crypto import salted_hmac


FINGERPRINT_SALT = "deareditors.editorial-letter.sender.v1"


def reader_fingerprint(user):
    """Return a stable opaque fingerprint without storing a user relation on a letter."""
    return salted_hmac(FINGERPRINT_SALT, str(user.pk), algorithm="sha256").hexdigest()
