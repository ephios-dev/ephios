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
        button = f'<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="{close}"></button>'
    return mark_safe(f"<div class='{' '.join(css_classes)}' role='alert'>{content}{button}</div>")
