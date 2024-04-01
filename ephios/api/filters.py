from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import BaseFilterBackend


class ParticipationPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        events = get_objects_for_user(request.user, "core.view_event")
        return queryset.filter(shift__event__in=events)
