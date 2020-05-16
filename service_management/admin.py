from django.contrib import admin

from service_management.models import (
    Shift,
    Participation,
    Resource,
    ResourcePosition,
    Service,
)

admin.site.register(Shift)
admin.site.register(Participation)
admin.site.register(Resource)
admin.site.register(ResourcePosition)
admin.site.register(Service)
