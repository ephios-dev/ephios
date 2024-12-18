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
    UserProfile,
    WorkingHours,
)
from ephios.core.models.events import PlaceholderParticipation
from ephios.core.models.users import IdentityProvider

admin.site.register(UserProfile)
admin.site.register(Qualification)
admin.site.register(QualificationGrant)
admin.site.register(QualificationCategory)
admin.site.register(WorkingHours)
admin.site.register(Consequence)

admin.site.register(Shift)
admin.site.register(Event, GuardedModelAdmin)
admin.site.register(EventType)
admin.site.register(LocalParticipation)
admin.site.register(PlaceholderParticipation)
admin.site.register(Notification)
admin.site.register(IdentityProvider)
