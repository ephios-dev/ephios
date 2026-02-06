from django.contrib import admin

from ephios.plugins.guests.models import GuestUser

admin.site.register(GuestUser)
