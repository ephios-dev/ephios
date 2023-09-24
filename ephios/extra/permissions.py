from functools import wraps
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.forms import BooleanField
from guardian.ctypes import get_content_type
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_group_obj_perms_model

Q_FALSE = Q(pk__in=[])


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        raise PermissionDenied

    return _wrapped_view


def _make_permission_names_qualified(permission_names, obj: Optional):
    """
    Return a list of permission names in the form "app_label.codename" for the given permissions codenames.
    If obj is given, the app_label is inferred from the object's meta.
    Otherwise, the permission name must already be qualified.
    """
    qualified_permission_names = []
    for name in permission_names or []:
        if "." in name:
            qualified_permission_names.append(name)
        elif obj is not None:
            app_label = obj._meta.app_label  # pylint: disable=protected-access
            qualified_permission_names.append(f"{app_label}.{name}")
        else:
            raise ValueError("Cannot infer permission app_label from name without obj")
    return qualified_permission_names


def get_groups_with_perms(obj=None, *, only_with_perms_in=None, must_have_all_perms=False):
    qs = Group.objects.all()
    qualified_permission_names = _make_permission_names_qualified(only_with_perms_in or [], obj)
    required_perms = get_permissions_from_qualified_names(qualified_permission_names)

    group_perms_model = get_group_obj_perms_model(obj)
    group_perms_rel_name = group_perms_model.group.field.related_query_name()
    obj_filter = {}
    if obj is not None:
        ctype = get_content_type(obj)
        if group_perms_model.objects.is_generic():
            obj_filter = {
                f"{group_perms_rel_name}__content_type": ctype,
                f"{group_perms_rel_name}__object_pk": obj.pk,
            }
        else:
            obj_filter = {f"{group_perms_rel_name}__content_object": obj}

    if must_have_all_perms:
        for perm in required_perms:
            if obj is not None:
                qs = qs.filter(
                    Q(permissions=perm)
                    | Q(
                        **{
                            f"{group_perms_rel_name}__permission": perm,
                            **obj_filter,
                        }
                    )
                )
            else:
                qs = qs.filter(permissions=perm)
    else:
        if obj is not None:
            qs = qs.filter(
                Q(permissions__in=required_perms)
                | Q(
                    **{
                        f"{group_perms_rel_name}__permission__in": required_perms,
                        **obj_filter,
                    }
                )
            )
        else:
            qs = qs.filter(Q(permissions__in=required_perms))
    return qs.distinct()


def get_permissions_from_qualified_names(qualified_names):
    perms_filter = Q_FALSE
    for qualified_name in qualified_names:
        app_label, codename = qualified_name.split(".")
        perms_filter = perms_filter | Q(content_type__app_label=app_label, codename=codename)
    return Permission.objects.filter(perms_filter)


class PermissionField(BooleanField):
    """
    This boolean field takes an additional list of permissions and a permission_target and ist true by default if the
    permission_target (user or group) has all given permissions.
    It requires a permission_target attribute on the form as well as calling the appropriate
    methods which is taken care of by PermissionFormMixin
    """

    def __init__(self, *args, **kwargs):
        self.permission_set = kwargs.pop("permissions")
        super().__init__(*args, required=kwargs.pop("required", False), **kwargs)

    def set_initial_value(self, user_or_group):
        self.target = user_or_group
        wanted_permission_objects = get_permissions_from_qualified_names(self.permission_set)
        self.initial = set(wanted_permission_objects) <= set(
            self._get_permissions_from_user_or_group(self.target)
        )

    def _get_permissions_from_user_or_group(self, user_or_group):
        if isinstance(user_or_group, get_user_model()):
            return user_or_group.user_permissions.all()
        return user_or_group.permissions.all()

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
        to_remove = []
        to_assign = []
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
