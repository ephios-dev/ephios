from django.forms import ModelForm
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.simpleresource.models import ResourceAllocation


class ResourceAllocationForm(BasePluginFormMixin, ModelForm):
    class Meta:
        model = ResourceAllocation
        fields = ["resources"]
        widgets = {
            "resources": Select2MultipleWidget,
        }

    def __init__(self, *args, shift, **kwargs):
        kwargs.setdefault("instance", ResourceAllocation.objects.get_or_create(shift=shift)[0])
        super().__init__(*args, **kwargs)

    @property
    def heading(self):
        return _("Resource allocation")

    def is_function_active(self):
        return bool(self.instance.resources.exists())
