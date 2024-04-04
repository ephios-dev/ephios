from rest_framework.permissions import DjangoModelPermissions, DjangoObjectPermissions


class ViewPermissionsMixin:
    # DjangoModelPermissions and DjangoObjectPermissions only check permissions for write/unsafe operations.
    # This mixin adds permissions for read/safe operations.
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class ViewPermissions(ViewPermissionsMixin, DjangoModelPermissions):
    pass


class ViewObjectPermissions(ViewPermissionsMixin, DjangoObjectPermissions):
    pass
