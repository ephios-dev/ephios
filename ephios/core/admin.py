from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from guardian.admin import GuardedModelAdmin

from ephios.core.forms.users import UserChangeForm, UserCreationForm
from ephios.core.models import (
    Consequence,
    Event,
    EventType,
    LocalParticipation,
    Qualification,
    QualificationCategory,
    QualificationGrant,
    Shift,
    UserProfile,
    WorkingHours,
)


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ("email", "first_name", "last_name", "is_staff")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "phone",
                )
            },
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "user_permissions")}),
    )

    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password",
                    "password_validation",
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "phone",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)
    filter_horizontal = ()


admin.site.register(UserProfile, UserAdmin)
admin.site.register(Qualification)
admin.site.register(QualificationGrant)
admin.site.register(QualificationCategory)
admin.site.register(WorkingHours)
admin.site.register(Consequence)

admin.site.register(Shift)
admin.site.register(Event, GuardedModelAdmin)
admin.site.register(EventType)
admin.site.register(LocalParticipation)
