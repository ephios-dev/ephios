from django.contrib import admin

from ephios.plugins.simpleresource.models import Resource, ResourceAllocation, ResourceCategory

admin.site.register(Resource)
admin.site.register(ResourceCategory)
admin.site.register(ResourceAllocation)
