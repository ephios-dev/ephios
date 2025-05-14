from django.apps import apps

from ephios.modellogging.log import LOGGED_MODELS


def test_all_models_registered():
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith("ephios."):
            continue
        for model_class in app_config.get_models():
            if getattr(model_class, "_ephios_dont_log", False):
                continue
            assert model_class in LOGGED_MODELS
