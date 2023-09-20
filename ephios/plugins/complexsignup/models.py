import uuid

from django.db import models
from django.db.models import Choices
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Qualification


class BuildingBlockType(Choices):
    atomic = "atomic"
    composite = "composite"


class BuildingBlock(models.Model):
    uuid = models.UUIDField("UUID", unique=True, default=uuid.uuid4)
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
        blank=False,
    )
    block_type = models.CharField(
        verbose_name=_("Type"), choices=BuildingBlockType.choices, max_length=64
    )

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

    def __str__(self):
        return self.name


class BlockQualificationRequirement(models.Model):
    block = models.ForeignKey(
        BuildingBlock, on_delete=models.CASCADE, related_name="qualification_requirements"
    )
    everyone = models.BooleanField()
    at_least = models.PositiveSmallIntegerField(
        default=0,
    )
    qualifications = models.ManyToManyField(Qualification)

    def __str__(self):
        if self.everyone:
            return _("everyone on {block} needs {qualifications}").format(
                block=self.block, qualifications=", ".join(map(str, self.qualifications.all()))
            )
        else:
            return _("at least {at_least} on {block} need {qualifications}").format(
                at_least=self.at_least,
                block=self.block,
                qualifications=f" {_('and')} ".join(map(str, self.qualifications.all())),
            )


class Position(models.Model):
    block = models.ForeignKey(BuildingBlock, on_delete=models.CASCADE, related_name="positions")
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

    def __str__(self):
        return self.label or f"{self.block.name} #{self.pk}"


class BlockComposition(models.Model):
    composite_block = models.ForeignKey(
        BuildingBlock, on_delete=models.CASCADE, related_name="sub_compositions"
    )
    sub_block = models.ForeignKey(
        BuildingBlock, on_delete=models.CASCADE, related_name="super_compositions"
    )
    optional = models.BooleanField(
        verbose_name=_("optional"),
        default=False,
    )
