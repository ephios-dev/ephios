from django.forms import BaseModelFormSet, BooleanField, ModelForm, modelformset_factory
from django.forms.formsets import DELETION_FIELD_NAME
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.simpleresource.models import ResourceAllocation, ResourceCategory


class ResourceAllocationForm(BasePluginFormMixin, ModelForm):
    class Meta:
        model = ResourceAllocation
        fields = ["resources"]
        widgets = {
            "resources": Select2MultipleWidget,
        }

    def __init__(self, *args, shift, **kwargs):
        kwargs.setdefault("prefix", "simple_resource")
        self.shift = shift
        try:
            kwargs.setdefault("instance", ResourceAllocation.objects.get(shift_id=shift.id))
        except (AttributeError, ResourceAllocation.DoesNotExist):
            pass
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        if self.cleaned_data.get("resources"):
            self.instance.shift = self.shift
            super().save(commit)
        elif self.instance.pk:
            self.instance.delete()

    @property
    def heading(self):
        return _("Resource allocation")

    def is_function_active(self):
        return bool(self.instance.resources.exists())


class BaseResourceCategoryFormset(BaseModelFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        initial_form_count = self.initial_form_count()
        if self.can_delete and (self.can_delete_extra or index < initial_form_count):
            category: ResourceCategory = form.instance
            form.fields[DELETION_FIELD_NAME] = BooleanField(
                label=_("Delete"),
                required=False,
                disabled=category.pk and category.resource_set.exists(),
            )


ResourceCategoryFormset = modelformset_factory(
    ResourceCategory,
    formset=BaseResourceCategoryFormset,
    can_delete=True,
    extra=0,
    fields=["name", "icon"],
)
