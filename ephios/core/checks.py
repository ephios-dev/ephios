import os

from django.conf import settings
from django.core.checks import Warning as DjangoWarning
from django.core.checks import register


@register("ephios", deploy=True)
def check_data_dir_is_not_inside_base_dir(app_configs, **kwargs):
    """
    On production setups, the data directory should
    not be inside the base directory (ephios package directory).
    """
    errors = []
    for name, directory in settings.DIRECTORIES.items():
        if os.path.commonpath([settings.BASE_DIR, directory]) == settings.BASE_DIR:
            errors.append(
                DjangoWarning(
                    "ephios data is stored near the ephios package directory.",
                    hint=f"You probably don't want to have {name} at {directory} to "
                    f"be inside or next to the ephios python package at "
                    f"{settings.BASE_DIR}! "
                    f"Configure ephios to use another location.",
                    id="ephios.W001",
                )
            )
    return errors
