from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.forms import BooleanField
from guardian.ctypes import get_content_type
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_group_obj_perms_model


class CustomPermissionRequiredMixin(PermissionRequiredMixin):
    """
    As of 2020-09-26, guardians permission mixin
    doesn't support the mode of operation we want, but Django's does:
    * Logged in users without permission get 403
    * not logged in users get redirected to login
    Therefore we patch Django's mixin to support object permissions
    """

    accept_global_perms = True
    accept_object_perms = True

    def get_permission_object(self):
        if hasattr(self, "permission_object"):
            return self.permission_object
        if hasattr(self, "get_object") and (obj := self.get_object()) is not None:
            return obj
        return getattr(self, "object", None)

    def has_permission(self):
        user = self.request.user
        perms = self.get_permission_required()
        if self.accept_global_perms and all(user.has_perm(perm) for perm in perms):
            return True
        if not self.accept_object_perms or (obj := self.get_permission_object()) is None:
            return False
        return all(user.has_perm(perm, obj) for perm in perms)


def get_groups_with_perms(obj, only_with_perms_in):
    ctype = get_content_type(obj)
    group_model = get_group_obj_perms_model(obj)

    group_rel_name = group_model.group.field.related_query_name()

    if group_model.objects.is_generic():
        group_filters = {
            "%s__content_type" % group_rel_name: ctype,
            "%s__object_pk" % group_rel_name: obj.pk,
        }
    else:
        group_filters = {"%s__content_object" % group_rel_name: obj}

    permission_ids = Permission.objects.filter(
        content_type=ctype, codename__in=only_with_perms_in
    ).values_list("id", flat=True)
    group_filters.update(
        {
            "%s__permission_id__in" % group_rel_name: permission_ids,
        }
    )
    return Group.objects.filter(**group_filters).distinct()


class StaffRequiredMixin(AccessMixin):
    """Verify that the current user is staff."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class PermissionField(BooleanField):
    def __init__(self, *args, **kwargs):
        self.permission_set = kwargs.pop("permissions")
        super().__init__(*args, **kwargs)

    def set_initial_value(self, user_or_group):
        self.target = user_or_group
        self.initial = self.target.permissions.filter(
            codename__in=map(lambda perm: perm.split(".")[-1], self.permission_set)
        ).exists()

    def update_permissions(self, assign):
        if assign:
            for permission in self.permission_set:
                assign_perm(permission, self.target)
        else:
            for permission in self.permission_set:
                remove_perm(permission, self.target)


class PermissionFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, PermissionField):
                field.set_initial_value(self.get_permission_target())

    def get_permission_target(self):
        return self.permission_target

    def save(self, commit=True):
        result = super().save(commit)
        for key, field in self.fields.items():
            if isinstance(field, PermissionField):
                field.update_permissions(self.cleaned_data[key])
        return result
