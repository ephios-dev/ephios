from django.contrib.auth.models import Group, Permission
from django.forms import BooleanField
from guardian.ctypes import get_content_type
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_group_obj_perms_model


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


class PermissionField(BooleanField):
    """
    This field takes a list of permissions and a permission_target and renders a checkbox that is checked if the target
    has all given permissions. It requires a permission_target attribute on the form as well as calling the appropriate
    methods which is taken care of by PermissionFormMixin
    """

    def __init__(self, *args, **kwargs):
        self.permission_set = kwargs.pop("permissions")
        super().__init__(*args, **kwargs)

    def set_initial_value(self, user_or_group):
        self.target = user_or_group
        self.initial = self.target.permissions.filter(
            codename__in=map(lambda perm: perm.split(".")[-1], self.permission_set)
        ).count() == len(self.permission_set)

    def update_permissions(self, target, assign):
        if assign:
            for permission in self.permission_set:
                assign_perm(permission, target)
        else:
            for permission in self.permission_set:
                remove_perm(permission, target)


class PermissionFormMixin:
    """
    Mixin for django.forms.ModelForm that handles permission updates for all ephios.extra.permissions.PermissionField on that form
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, PermissionField) and self.instance.pk is not None:
                field.set_initial_value(self.permission_target)

    def save(self, commit=True):
        target = super().save(commit)
        for key, field in self.fields.items():
            if isinstance(field, PermissionField) and key in self.changed_data:
                field.update_permissions(target, self.cleaned_data[key])
        return target
