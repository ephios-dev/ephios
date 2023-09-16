from django.db import models
from django.db.models import Choices
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Qualification


class BuildingBlockType(Choices):
    atomic = _("atomic")
    composite = _("composite")


class BuildingBlock(models.Model):
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
        blank=False,
    )
    block_type = models.CharField(verbose_name=_("Type"), choices=BuildingBlockType.choices)

    # composite blocks
    sub_blocks = models.ManyToManyField(
        "self", through="BlockComposition", through_fields=("composite_block", "sub_block")
    )

    # atomic blocks
    allow_more = models.BooleanField(
        verbose_name=_("allow more"),
        help_text=_("Allow more participants that qualify for any of the positions."),
        default=False,
    )


class BlockQualificationRequirement(models.Model):
    block = models.ForeignKey(
        BuildingBlock, on_delete=models.CASCADE, related_name="qualification_requirements"
    )
    everyone = models.BooleanField()
    at_least = models.PositiveSmallIntegerField(
        default=0,
    )
    qualifications = models.ManyToManyField(Qualification)


class Position(models.Model):
    label = models.CharField(
        verbose_name=_("Label"),
        max_length=255,
        blank=True,
    )
    optional = models.BooleanField(
        verbose_name=_("optional"),
        default=False,
    )
    qualifications = models.ManyToManyField(
        Qualification,
        verbose_name=_("required qualifications"),
        blank=True,
    )


class BlockComposition(models.Model):
    composite_block = models.ForeignKey(BuildingBlock, on_delete=models.CASCADE)
    sub_block = models.ForeignKey(BuildingBlock, on_delete=models.CASCADE)
    optional = models.BooleanField(
        verbose_name=_("optional"),
        default=False,
    )
