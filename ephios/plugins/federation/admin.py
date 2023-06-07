from django.contrib import admin

from ephios.plugins.federation.models import FederatedEventShare, FederatedGuest, FederatedHost

admin.site.register(FederatedGuest)
admin.site.register(FederatedHost)
admin.site.register(FederatedEventShare)
