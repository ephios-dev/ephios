from crispy_forms.exceptions import CrispyError
from crispy_forms.utils import TEMPLATE_PACK
from django import template
from django.conf import settings
from django.forms import boundfield
from django.template import Context
from django.template.loader import get_template

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


@register.filter(name="consequence_formset_field")
def consequence_formset_field(field):
    # inspired by as_crispy_field, but it is not callable as filter and does not support wrapper class
    if not isinstance(field, boundfield.BoundField) and settings.DEBUG:
        raise CrispyError("|as_crispy_field got passed an invalid or inexistent field")

    attributes = {
        "field": field,
        "form_show_errors": True,
        "form_show_labels": True,
        "label_class": "col-md-4",
        "field_class": "col-md-8",
        "wrapper_class": "row",
    }

    helper = getattr(field.form, "helper", None)
    template_path = None
    if helper is not None:
        attributes.update(helper.get_attributes(TEMPLATE_PACK))
        template_path = helper.field_template
    if not template_path:
        template_path = "%s/field.html" % TEMPLATE_PACK
    template = get_template(template_path)

    c = Context(attributes).flatten()
    return template.render(c)
