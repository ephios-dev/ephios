import guardian.mixins
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import Permission, Group
from django.contrib.auth.views import redirect_to_login
from guardian.ctypes import get_content_type
from guardian.utils import get_group_obj_perms_model

from jep import settings


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
        {"%s__permission_id__in" % group_rel_name: permission_ids,}
    )
    return Group.objects.filter(**group_filters).distinct()


class CustomPermissionRequiredMixin(guardian.mixins.PermissionRequiredMixin):
    raise_exception = True
    accept_global_perms = True

    def on_permission_check_fail(self, request, response, obj=None):
        if request.user.is_authenticated:
            return response
        else:
            return redirect_to_login(
                self.request.get_full_path(), settings.LOGIN_URL, REDIRECT_FIELD_NAME
            )
