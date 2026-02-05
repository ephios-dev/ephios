from django.contrib import admin

from ephios.plugins.complexsignup.models import (
    BlockComposition,
    BlockQualificationRequirement,
    BuildingBlock,
    Position,
)

admin.site.register(BuildingBlock)
admin.site.register(Position)
admin.site.register(BlockQualificationRequirement)
admin.site.register(BlockComposition)
