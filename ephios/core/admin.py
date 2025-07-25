from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from ephios.core.models import (
    LocalConsequence,
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
from ephios.core.models.events import ParticipationComment, PlaceholderParticipation
from ephios.core.models.users import IdentityProvider

admin.site.register(UserProfile)
admin.site.register(Qualification)
admin.site.register(QualificationGrant)
admin.site.register(QualificationCategory)
admin.site.register(WorkingHours)
admin.site.register(LocalConsequence)

admin.site.register(Shift)
admin.site.register(Event, GuardedModelAdmin)
admin.site.register(EventType)
admin.site.register(LocalParticipation)
admin.site.register(PlaceholderParticipation)
admin.site.register(Notification)
admin.site.register(IdentityProvider)
admin.site.register(ParticipationComment)
