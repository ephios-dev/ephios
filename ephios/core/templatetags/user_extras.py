from django import template

from ephios.core.consequences import editable_consequences

register = template.Library()


@register.filter(name="editable_consequences")
def editable_consequences_tag(user, states=None):
    qs = editable_consequences(user)
    if states:
        qs = qs.filter(state__in=states.split(" "))
    return qs


@register.filter(name="workhour_items")
def workhour_items(user):
    return user.get_workhour_items()


@register.filter(name="qualifications_in")
def qualifications_by_category(user, qualification_category):
    # return Qualification.objects.filter(pk__in=user.qualification_grants.filter(
    #             Q(expires__gt=timezone.now()) | Q(expires__isnull=True)
    #         ).values_list("qualification_id", flat=True), category=qualification_category)
    return user.qualification_grants.filter(qualification__category=qualification_category)
