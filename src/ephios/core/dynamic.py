class DynamicSettingsProxy:
    """
    Proxy access to django settings but first check if any receiver overwrites it with a dynamic value.
    """

    NONE = object()

    def __init__(self):
        from django.conf import settings

        self._django_settings = settings

    def __getattr__(self, name):
        from ephios.core.signals import provide_dynamic_settings

        for __, result in provide_dynamic_settings.send(None, name=name):
            if result is not None:
                if result is DynamicSettingsProxy.NONE:
                    return None
                return result
        # default to django settings
        return getattr(self._django_settings, self.get_default_key(name))

    def get_default_key(self, settings_key):
        return f"DEFAULT_{settings_key}"


dynamic_settings = DynamicSettingsProxy()
