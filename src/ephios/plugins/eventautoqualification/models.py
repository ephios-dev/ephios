from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Event, Qualification
from ephios.core.models.users import ExpirationDateField
from ephios.modellogging.log import ModelFieldsLogConfig, register_model_for_logging


class EventAutoQualificationConfiguration(models.Model):
    event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="auto_qualification_config"
    )

    qualification = models.ForeignKey(
        Qualification, on_delete=models.CASCADE, verbose_name=_("Qualification")
    )
    expiration_date = ExpirationDateField(verbose_name=_("Expiration date"), null=True, blank=True)

    class Modes(models.IntegerChoices):
        ANY_SHIFT = 1, _("any shift")
        EVERY_SHIFT = 2, _("every shift")
        LAST_SHIFT = 3, _("last shift")

    mode = models.IntegerField(
        choices=Modes.choices,
        default=Modes.ANY_SHIFT,
        verbose_name=_("Required attendance"),
    )

    extend_only = models.BooleanField(
        default=False, verbose_name=_("Only extend or reactivate existing qualification")
    )
    needs_confirmation = models.BooleanField(
        default=True, verbose_name=_("Qualification must be confirmed afterwards")
    )

    def __str__(self):
        return str(self.qualification or self.event)

    class Meta:
        verbose_name = _("event auto qualification configuration")


register_model_for_logging(
    EventAutoQualificationConfiguration,
    ModelFieldsLogConfig(
        unlogged_fields=["id", "event"],
        attach_to_func=lambda instance: (Event, instance.event_id),
    ),
)
