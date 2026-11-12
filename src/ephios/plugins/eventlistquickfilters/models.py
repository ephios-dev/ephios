from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.modellogging.log import dont_log


@dont_log
class EventListQuickFilter(models.Model):
    label = models.CharField(max_length=255)
    position = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Position"),
        help_text=_(
            "The position of this filter in the list of filters. Lower numbers will be shown first."
        ),
    )
    visible_for_groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="visible_quick_filters",
        verbose_name=_("Visible to groups"),
        help_text=_("These groups can see this filter button."),
    )
    default_for_groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="default_quick_filters",
        verbose_name=_("Default for groups"),
        help_text=_("This filter is selected by default for these groups."),
    )
    show_all_types_on_deactivation = models.BooleanField(
        default=True,
        verbose_name=_("Show all event types when turned off"),
        help_text=_(
            "If this is checked, deactivating this filter will show all event types. "
            "If this is unchecked, deactivating this filter will show the default filter for the user."
        ),
    )
    filter_types = models.ManyToManyField(
        "core.EventType",
        related_name="quick_filters",
        blank=True,
        verbose_name=_("Event types"),
        help_text=_(
            "Choose the event types shown when this filter is active. Leave this empty "
            "to include all event types."
        ),
    )

    class Meta:
        verbose_name = _("Event List Quick Filter")
        verbose_name_plural = _("Event List Quick Filters")
        ordering = ["position"]

    def __str__(self):
        return self.label

    def get_types_ids(self):
        return list(self.filter_types.values_list("id", flat=True))
