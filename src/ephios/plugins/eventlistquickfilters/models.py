from django.db import models
from django.utils.translation import gettext_lazy as _


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
        verbose_name=_("Visible for Groups"),
    )
    default_for_groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="default_quick_filters",
        verbose_name=_("Default for Groups"),
    )
    filter_types = models.ManyToManyField(
        "core.EventType",
        related_name="quick_filters",
        blank=True,
        verbose_name=_("Filter Event Types"),
        help_text=_(
            "An empty selection is ambigous, as it could mean 'show all' or 'use default filter', "
            "so make sure a filter with an empty selection is used as a default."
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

    def mark_is_active(self, request, used_as_default=False):
        """
        Set a flag on this object based on the GET parameters of the given request.
        This can be used in templates to highlight an active filter.
        """
        GET_types = set(request.GET.getlist("types"))
        filter_types = set(map(str, self.get_types_ids()))
        # if no types are given, a potential default filter is active
        self.used_as_default = used_as_default  # can be used in templates to use empty GET.types
        if not GET_types and used_as_default:
            self.is_active = True
            return
        self.is_active = GET_types == filter_types
