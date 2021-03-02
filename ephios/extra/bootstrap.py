from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _


def render_alert(content, alert_type=None, dismissible=True):
    """Render a Bootstrap alert."""
    button = ""
    if not alert_type:
        alert_type = "info"
    css_classes = ["alert", f"alert-{alert_type}"]
    if dismissible:
        css_classes.append("alert-dismissible")
        close = _("close")
        button = (
            '<button type="button" class="close" data-dismiss="alert" aria-label="{close}">&times;</button>'
        ).format(close=close)
    return mark_safe(
        "<div class='{classes}' role='alert'>{button}{content}</div>".format(
            classes=" ".join(css_classes), button=button, content=content
        )
    )
