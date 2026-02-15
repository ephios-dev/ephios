from django.utils.translation import gettext_lazy as _

from ephios.plugins.baseshiftstructures.structure.common import (
    QualificationMinMaxBaseShiftStructure,
)


class UniformShiftStructure(QualificationMinMaxBaseShiftStructure):
    slug = "uniform"
    verbose_name = _("Uniform")
    description = _("Everyone in the shift has the same requirements.")
