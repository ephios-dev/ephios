from django.contrib.auth.models import Group
from django.forms import ModelForm, ModelMultipleChoiceField, formset_factory, modelformset_factory
from guardian.shortcuts import get_objects_for_user, assign_perm

from event_management.models import Event, Shift


class EventForm(ModelForm):
    visible_for = ModelMultipleChoiceField(queryset=Group.objects.none())

    class Meta:
        model = Event
        fields = ["title", "description", "location", "type"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields["visible_for"].queryset = get_objects_for_user(
            self.user, "publish_event_for_group", klass=Group
        )

    def save(self, commit=True):
        event = super(EventForm, self).save(commit)
        for group in self.cleaned_data["visible_for"]:
            assign_perm("view_event", group, event)
        return event


ShiftFormSet = modelformset_factory(
    Shift, fields=("meeting_time", "start_time", "end_time"), extra=5
)
