from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from guardian.ctypes import get_content_type
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
