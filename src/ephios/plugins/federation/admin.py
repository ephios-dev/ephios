from django.contrib import admin

from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    FederatedParticipation,
    FederatedUser,
    InviteCode,
)

admin.site.register(FederatedGuest)
admin.site.register(FederatedHost)
admin.site.register(FederatedEventShare)
admin.site.register(FederatedUser)
admin.site.register(FederatedParticipation)
admin.site.register(InviteCode)
