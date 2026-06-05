import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet():
    raw_key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if raw_key:
        key = raw_key.encode("utf-8")
    else:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


class EncryptedTextField(models.TextField):
    description = "TextField encrypted with Fernet before database storage"

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if str(value).startswith("gAAAA"):
            return value
        return _fernet().encrypt(str(value).encode("utf-8")).decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return value

    def to_python(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, str) and value.startswith("gAAAA"):
            try:
                return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
            except InvalidToken:
                return value
        return value
