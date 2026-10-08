from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Shift
from ephios.modellogging.log import ModelFieldsLogConfig, register_model_for_logging


class ResourceCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name=_("Name"))
    icon = models.CharField(
        max_length=50, default="box", verbose_name=_("Icon"), help_text="FontAwesome icon name"
    )

    class Meta:
        verbose_name = _("Resource category")
        verbose_name_plural = _("Resource categories")

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.name


register_model_for_logging(
    ResourceCategory,
    ModelFieldsLogConfig(),
)


class Resource(models.Model):
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    category = models.ForeignKey(
        ResourceCategory, on_delete=models.CASCADE, verbose_name=_("Category")
    )

    class Meta:
        verbose_name = _("Resource")
        verbose_name_plural = _("Resources")

    def __str__(self):
        # pylint: disable=invalid-str-returned
        return self.title


register_model_for_logging(
    Resource,
    ModelFieldsLogConfig(),
)


class ResourceAllocation(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, verbose_name=_("Shift"))
    resources = models.ManyToManyField(Resource, blank=True, verbose_name=_("Resources"))

    class Meta:
        verbose_name = _("Resource allocation")
        verbose_name_plural = _("Resource allocations")

    def __str__(self):
        return str(self.shift)


register_model_for_logging(
    ResourceAllocation,
    ModelFieldsLogConfig(attach_to_func=lambda allocation: (Shift, allocation.shift_id)),
)
