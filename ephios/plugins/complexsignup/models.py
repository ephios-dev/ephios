import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Qualification
from ephios.modellogging.log import ModelFieldsLogConfig, register_model_for_logging


class BuildingBlockType(models.TextChoices):
    ATOMIC = "atomic", _("atomic")
    COMPOSITE = "composite", _("composite")


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
        "self",
        through="BlockComposition",
        through_fields=("composite_block", "sub_block"),
        verbose_name=_("sub blocks"),
    )

    # atomic blocks
    allow_more = models.BooleanField(
        verbose_name=_("allow more"),
        help_text=_("Allow more participants that qualify for any of the positions."),
        default=False,
    )

    def __str__(self):
        return str(self.name)

    def is_composite(self):
        return self.block_type == BuildingBlockType.COMPOSITE.COMPOSITE.value

    class Meta:
        verbose_name = _("building block")
        verbose_name_plural = _("building blocks")


register_model_for_logging(
    BuildingBlock,
    ModelFieldsLogConfig(
        unlogged_fields=["uuid", "id"],
    ),
)


class BlockQualificationRequirement(models.Model):
    block = models.ForeignKey(
        BuildingBlock,
        on_delete=models.CASCADE,
        related_name="qualification_requirements",
        verbose_name=_("block"),
    )
    everyone = models.BooleanField(
        verbose_name=_("everyone"),
    )
    at_least = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("at least"),
    )
    qualifications = models.ManyToManyField(
        Qualification, verbose_name=_("required qualifications")
    )

    def __str__(self):
        if self.everyone:
            return _("everyone on {block} needs {qualifications}").format(
                block=self.block, qualifications=", ".join(map(str, self.qualifications.all()))
            )
        return _("at least {at_least} on {block} need {qualifications}").format(
            at_least=self.at_least,
            block=self.block,
            qualifications=f" {_('and')} ".join(map(str, self.qualifications.all())),
        )

    class Meta:
        verbose_name = _("qualification requirement")
        verbose_name_plural = _("qualification requirements")


register_model_for_logging(
    BlockQualificationRequirement,
    ModelFieldsLogConfig(
        unlogged_fields=["block", "id"],
        attach_to_func=lambda instance: (BuildingBlock, instance.pk),
    ),
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
        return _("{label_or_pk} on {block_name}").format(
            label_or_pk=self.label or self.pk, block_name=self.block.name
        )

    class Meta:
        verbose_name = _("position")
        verbose_name_plural = _("positions")


register_model_for_logging(
    Position,
    ModelFieldsLogConfig(
        unlogged_fields=["block", "id"],
        attach_to_func=lambda instance: (BuildingBlock, instance.block.pk),
    ),
)


class BlockComposition(models.Model):
    composite_block = models.ForeignKey(
        BuildingBlock,
        on_delete=models.CASCADE,
        related_name="sub_compositions",
        verbose_name=_("composite block"),
    )
    sub_block = models.ForeignKey(
        BuildingBlock,
        on_delete=models.CASCADE,
        related_name="super_compositions",
        verbose_name=_("sub block"),
    )
    label = models.CharField(
        verbose_name=_("Label"),
        max_length=255,
        blank=True,
    )
    optional = models.BooleanField(
        verbose_name=_("optional"),
        default=False,
    )

    def __str__(self):
        return _("{label} on {composite_blocK}").format(
            label=self.label or f"{self.sub_block.name} #{self.id}",
            composite_blocK=self.composite_block,
        )

    class Meta:
        verbose_name = _("block composition")
        verbose_name_plural = _("block compositions")


register_model_for_logging(
    BlockComposition,
    ModelFieldsLogConfig(
        unlogged_fields=["composite_block", "id"],
        attach_to_func=lambda instance: (BuildingBlock, instance.composite_block.pk),
    ),
)
