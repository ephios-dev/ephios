from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Event
from ephios.core.signup import Qualification


class EventAutoQualificationConfiguration(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="auto_qualification_config"
    )

    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
    expiration_date = models.DateField(verbose_name=_("Expiration date"), null=True, blank=True)

    class Modes(models.IntegerChoices):
        ANY_SHIFT = 1, _("any shift")
        EVERY_SHIFT = 2, _("every shift")
        LAST_SHIFT = 3, _("last shift")

    mode = models.IntegerField(
        choices=Modes.choices,
        default=Modes.ANY_SHIFT,
        verbose_name=_("Which shifts must be attended to acquire the qualification?"),
    )

    extend_only = models.BooleanField(
        default=False, verbose_name=_("Only extend or reactivate existing qualification")
    )
    needs_confirmation = models.BooleanField(
        default=True, verbose_name=_("Qualification must be confirmed afterwards")
    )
