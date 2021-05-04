from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if not value and key in params:
            del params[key]
        else:
            params[key] = str(value)
    return params.urlencode(safe="[]")
