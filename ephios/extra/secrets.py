import os
import string

from django.utils.crypto import get_random_string


def django_secret_from_file(path: str):
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    chars = string.ascii_letters + string.digits + string.punctuation
    secret = get_random_string(50, chars)
    with open(path, "w") as f:
        os.chmod(path, 0o600)
        try:
            os.chown(path, os.getuid(), os.getgid())
        except AttributeError:
            pass  # os.chown is not available on Windows
        f.write(secret)
    return secret