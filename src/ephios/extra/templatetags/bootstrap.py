from django import template

from ephios.extra.bootstrap import render_alert

register = template.Library()


@register.simple_tag(name="render_alert")
def render_alert_tag(content, alert_type="info", dismissible=True):
    return render_alert(content, alert_type, dismissible)


@register.filter(name="formset_errors")
def formset_errors(formset):
    if errors := formset.non_form_errors():
        return render_alert("<br>".join(errors), alert_type="danger")
    return ""
