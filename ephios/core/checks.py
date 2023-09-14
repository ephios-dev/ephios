import os

from django.conf import settings
from django.core.checks import Error as DjangoError
from django.core.checks import Warning as DjangoWarning
from django.core.checks import register


@register("ephios", deploy=True)
def check_ephios_deploy_settings(app_configs, **kwargs):
    # On production setups, the data directory should
    # not be inside the base directory (ephios package directory).
    errors = []

    bad_directories = []
    for name, directory in settings.DIRECTORIES.items():
        if os.path.commonpath([settings.BASE_DIR, directory]) == settings.BASE_DIR:
            bad_directories.append((name, directory))
    if bad_directories:
        errors.append(
            DjangoWarning(
                "ephios data is stored near the ephios package directory.",
                hint=f"You probably don't want to have the {', '.join(name for name, _ in bad_directories)} "
                f"be inside or next to the ephios python package at "
                f"{settings.BASE_DIR}! "
                f"Configure ephios to use another location.",
                id="ephios.W001",
            )
        )

    # Check that VAPID keys were used to configure webpush.
    if not settings.WEBPUSH_SETTINGS:
        errors.append(
            DjangoWarning(
                "WEBPUSH_SETTINGS are not configured.",
                hint="You need to generate a vapid key using ./manage.py generate_vapid_key in order to "
                "use push notifications.",
                id="ephios.W002",
            )
        )

    if not os.access(settings.MEDIA_ROOT, os.W_OK):
        errors.append(
            DjangoError(
                "Media root not writable by application server.",
                hint=f"You need to make sure that the application server can write to the media root at "
                f"{settings.MEDIA_ROOT}.",
                id="ephios.E001",
            )
        )

    return errors
