import random
import string

from django.core.cache import cache


def file_ticket(file):
    key = "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(32)
    )
    cache.set(key, file, 60 * 60)
    return key
