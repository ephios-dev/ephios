from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from ephios.core.models import (
    Consequence,
    Event,
    EventType,
    LocalParticipation,
    Notification,
    Qualification,
    QualificationCategory,
    QualificationGrant,
    Shift,
    WorkingHours,
)

admin.site.register(Qualification)
admin.site.register(QualificationGrant)
admin.site.register(QualificationCategory)
admin.site.register(WorkingHours)
admin.site.register(Consequence)

admin.site.register(Shift)
admin.site.register(Event, GuardedModelAdmin)
admin.site.register(EventType)
admin.site.register(LocalParticipation)
admin.site.register(Notification)
