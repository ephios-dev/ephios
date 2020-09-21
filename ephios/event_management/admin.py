from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from ephios.event_management.models import Event, EventType, LocalParticipation, Shift

admin.site.register(Shift)
admin.site.register(Event, GuardedModelAdmin)
admin.site.register(EventType)
admin.site.register(LocalParticipation)
