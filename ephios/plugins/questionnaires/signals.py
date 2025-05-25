from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ephios.core.signals import nav_link, register_group_permission_fields
from ephios.extra.permissions import PermissionField


@receiver(nav_link, dispatch_uid="ephios.plugins.questionnaires.signals.nav_link")
def add_nav_link(sender, request, **kwargs):
    return (
        [
            {
                "label": _("Questions"),
                "url": reverse_lazy("questionnaires:question_list"),
                "active": request.resolver_match
                and request.resolver_match.app_name == "questionnaires",
                "group": _("Management"),
            }
        ]
        if request.user.has_perm("questionnaires.view_question")
        else []
    )


@receiver(
    register_group_permission_fields,
    dispatch_uid="ephios.plugins.questionnaires.signals.register_group_permission_fields",
)
def group_permission_fields(sender, **kwargs):
    return [
        (
            "manage_questions",
            PermissionField(
                label=_("Manage Questions"),
                help_text=_("Enables this group to add questions that can be asked during signup."),
                permissions=[
                    "questionnaires.view_question",
                    "questionnaires.add_question",
                    "questionnaires.change_question",
                    "questionnaires.delete_question",
                ],
            ),
        )
    ]
