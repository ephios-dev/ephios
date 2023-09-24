from crispy_forms.exceptions import CrispyError
from crispy_forms.utils import TEMPLATE_PACK
from django.forms import boundfield
from django.template import Context, Template
from django.template.loader import get_template


class AbortLink:
    """
    a-tag to cancel the form as a bootstrap button
    """

    def __init__(self, href):
        self.href = href

    def render(self, form, context, template_pack=TEMPLATE_PACK, **kwargs):
        context.update({"href": self.href})
        return Template(
            '{% load i18n %}<a role="button" class="btn btn-secondary mt-1" href="{{ href }}">{% translate "Cancel" %}</a>'
        ).render(context)


def as_crispy_field(
    field,
    template_pack=TEMPLATE_PACK,
    label_class="",
    field_class="",
    wrapper_class="",
    show_labels=True,
):
    # inspired by original as_crispy_field, but it is not callable as filter and does not support wrapper class/labels
    from django.conf import settings

    if not isinstance(field, boundfield.BoundField) and settings.DEBUG:
        raise CrispyError("|as_crispy_field got passed an invalid or inexistent field")

    attributes = {
        "field": field,
        "form_show_errors": True,
        "form_show_labels": show_labels,
        "label_class": label_class,
        "field_class": field_class,
        "wrapper_class": wrapper_class,
    }
    helper = getattr(field.form, "helper", None)

    template_path = None
    if helper is not None:
        attributes.update(helper.get_attributes(template_pack))
        template_path = helper.field_template
    if not template_path:
        template_path = f"{template_pack}/field.html"
    template = get_template(template_path)

    c = Context(attributes).flatten()
    return template.render(c)
