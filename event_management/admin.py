from django.contrib import admin

from event_management.models import Event, EventType, LocalParticipation, Shift

admin.site.register(Shift)
admin.site.register(Event)
admin.site.register(EventType)
admin.site.register(LocalParticipation)
