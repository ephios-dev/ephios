from django.contrib.auth.models import Group, Permission
from guardian.ctypes import get_content_type
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
