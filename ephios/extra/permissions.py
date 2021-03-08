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
        codename_set = set(map(lambda perm: perm.split(".")[-1], self.permission_set))
        self.initial = codename_set <= set(
            self.target.permissions.values_list("codename", flat=True)
        )

    def assign_permissions(self, target):
        for permission in self.permission_set:
            assign_perm(permission, target)

    def remove_permissions(self, target):
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
        to_remove = list()
        to_assign = list()
        for key, field in self.fields.items():
            if isinstance(field, PermissionField):
                if self.cleaned_data[key]:
                    to_assign.append(field)
                else:
                    to_remove.append(field)
        for field in to_remove:
            field.remove_permissions(target)
        for field in to_assign:
            field.assign_permissions(target)
        return target
