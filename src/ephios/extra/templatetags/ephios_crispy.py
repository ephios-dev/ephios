from django import template

from ephios.extra.crispy import as_crispy_field

register = template.Library()


@register.simple_tag(name="crispy_field")
def crispy_field(field, label_class="", field_class="", wrapper_class="", show_labels=True):
    return as_crispy_field(
        field,
        label_class=label_class,
        field_class=field_class,
        wrapper_class=wrapper_class,
        show_labels=show_labels,
    )
