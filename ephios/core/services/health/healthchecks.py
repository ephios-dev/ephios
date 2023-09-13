import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.dynamic_preferences_registry import LastRunPeriodicCall
from ephios.core.signals import register_healthchecks

# health checks are meant to monitor the health of the application while it is running
# in contrast there are django checks which are meant to check the configuration of the application


def run_healthchecks():
    for _, healthchecks in register_healthchecks.send(None):
        for HealthCheck in healthchecks:
            check = HealthCheck()
            status, message = check.check()
            yield check, status, message


class HealthCheckStatus:
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class AbstractHealthCheck:
    @property
    def slug(self):
        """
        Return a unique slug for this health check.
        """
        raise NotImplementedError

    @property
    def name(self):
        """
        Return a short name of this health check.
        """
        raise NotImplementedError

    @property
    def description(self):
        """
        Return a short description of this health check.
        """
        raise NotImplementedError

    @property
    def documentation_link(self):
        """
        Return a link to the documentation of this health check.
        """
        return None

    def check(self):
        """
        Return a tuple of (status, message) where status is one of HealthCheckStatus
        """
        raise NotImplementedError


class DBHealthCheck(AbstractHealthCheck):
    slug = "db"
    name = _("Database")
    description = _("The database is the central storage for all data.")
    documentation_link = "https://docs.djangoproject.com/en/stable/ref/databases/"

    def check(self):
        from django.db import connection

        try:
            connection.cursor()
            Permission.objects.exists()
        except Exception as e:
            return HealthCheckStatus.ERROR, str(e)

        if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
            return HealthCheckStatus.WARNING, _(
                "Using SQLite, which should not be used in production."
            )

        return HealthCheckStatus.OK, _("Database connection established.")


class CacheHealthCheck(AbstractHealthCheck):
    slug = "cache"
    name = _("Cache")
    description = _("The cache is used to store temporary data.")
    documentation_link = "https://docs.djangoproject.com/en/stable/topics/cache/"

    def check(self):
        from django.core import cache

        try:
            cache.cache.set("_healthcheck", "1")
            if not cache.cache.get("_healthcheck") == "1":
                raise Exception("Cache not available")
        except Exception as e:
            return HealthCheckStatus.ERROR, str(e)

        if (
            settings.CACHES.get("default", {}).get("BACKEND")
            == "django.core.cache.backends.locmem.LocMemCache"
        ):
            return HealthCheckStatus.WARNING, _(
                "Using LocMemCache, which should not be used in production."
            )

        return HealthCheckStatus.OK, _("Cache connection established.")


class CronJobHealthCheck(AbstractHealthCheck):
    slug = "cronjob"
    name = _("Cronjob")
    description = _(
        "A cron job must regularly call ephios to do recurring tasks like sending notifications."
    )
    documentation_link = (
        "https://docs.ephios.de/en/stable/admin/deployment/manual/index.html#setup-cron"
    )

    def check(self):
        last_call = LastRunPeriodicCall.get_last_call()
        if LastRunPeriodicCall.is_stuck():
            if last_call:
                return (
                    HealthCheckStatus.WARNING,
                    mark_safe(
                        _("Cronjob stuck, last run {last_call}.").format(
                            last_call=naturaltime(last_call),
                        )
                    ),
                )
            else:
                return (
                    HealthCheckStatus.ERROR,
                    mark_safe(_("Cronjob stuck, no last run.")),
                )
        else:
            return (
                HealthCheckStatus.OK,
                mark_safe(_("Last run {last_call}.").format(last_call=naturaltime(last_call))),
            )


class WritableMediaRootHealthCheck(AbstractHealthCheck):
    slug = "writable_media_root"
    name = _("Writable Media Root")
    description = _("The media root must be writable by the application server.")
    documentation_link = (
        "https://docs.ephios.de/en/stable/admin/deployment/manual/index.html#data-directory"
    )

    def check(self):
        media_root = Path(settings.MEDIA_ROOT)
        if not os.access(media_root, os.W_OK):
            return (
                HealthCheckStatus.ERROR,
                mark_safe(_("Media root not writable by application server.")),
            )
        return (
            HealthCheckStatus.OK,
            mark_safe(_("Media root is writable by application server.")),
        )


@receiver(register_healthchecks, dispatch_uid="ephios.core.healthchecks.register_core_healthchecks")
def register_core_healthchecks(sender, **kwargs):
    yield DBHealthCheck
    yield CacheHealthCheck
    yield CronJobHealthCheck
    yield WritableMediaRootHealthCheck
