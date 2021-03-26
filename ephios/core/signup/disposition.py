from django import forms
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import AbstractParticipation, Shift, UserProfile
from ephios.extra.mixins import CustomPermissionRequiredMixin


class BaseDispositionParticipationForm(forms.ModelForm):
    disposition_participation_template = "core/disposition/fragment_participation.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.can_delete = self.instance.state == AbstractParticipation.States.GETTING_DISPATCHED
        try:
            self.shift = self.instance.shift
        except AttributeError as e:
            raise ValueError(f"{type(self)} must be initialized with an instance.") from e

    class Meta:
        model = AbstractParticipation
        fields = ["state"]
        widgets = dict(state=forms.HiddenInput(attrs={"class": "state-input"}))


class DispositionBaseModelFormset(forms.BaseModelFormSet):
    """
    To allow us to dynamically add server-side rendered forms to a formset
    we patch a way to change the starting index.
    """

    def __init__(self, *args, start_index=0, **kwargs):
        self._start_index = start_index
        super().__init__(*args, **kwargs)

    def add_prefix(self, index):
        return "%s-%s" % (self.prefix, self._start_index + index)

    def delete_existing(self, obj, commit=True):
        # refresh from db as obj has the state from the post data
        db_obj = AbstractParticipation.objects.get(id=obj.id)
        if db_obj.state != AbstractParticipation.States.GETTING_DISPATCHED:
            raise ValueError(
                "Deletion a participation is only allowed if it was just added through disposition."
            )
        super().delete_existing(obj, commit)


def get_disposition_formset(form):
    return forms.modelformset_factory(
        model=AbstractParticipation,
        formset=DispositionBaseModelFormset,
        form=form,
        extra=0,
        can_order=False,
        can_delete=True,
    )


def addable_users(shift):
    """
    Return queryset of user objects that can be added to the shift.
    This also includes users that already have a participation, as that might have gotten removed in JS.

    This also includes users that can normally not see the event. The permission will be added accordingly.
    If needed, this method could be moved to signup methods.
    """
    return UserProfile.objects.all()


class AddUserForm(forms.Form):
    user = forms.ModelChoiceField(
        widget=ModelSelect2Widget(
            model=UserProfile,
            search_fields=["first_name__icontains", "last_name__icontains"],
            attrs={"form": "add-user-form", "data-placeholder": _("search")},
        ),
        queryset=UserProfile.objects.none(),  # set using __init__
    )
    new_index = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, user_queryset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = user_queryset


class DispositionBaseViewMixin(CustomPermissionRequiredMixin, SingleObjectMixin):
    permission_required = "core.change_event"
    model = Shift

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object: Shift = self.get_object()

    def dispatch(self, request, *args, **kwargs):
        if self.object.signup_method.disposition_participation_form_class is None:
            raise Http404(_("This signup method does not support disposition."))
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.object.event


class AddUserView(DispositionBaseViewMixin, TemplateResponseMixin, View):
    def get_template_names(self):
        return [
            self.object.signup_method.disposition_participation_form_class.disposition_participation_template
        ]

    def post(self, request, *args, **kwargs):
        shift = self.object
        form = AddUserForm(
            data=request.POST,
            user_queryset=addable_users(shift),
        )
        if form.is_valid():
            user: UserProfile = form.cleaned_data["user"]
            instance = shift.signup_method.get_participation_for(user.as_participant())
            instance.state = AbstractParticipation.States.GETTING_DISPATCHED
            instance.save()

            DispositionParticipationFormset = get_disposition_formset(
                self.object.signup_method.disposition_participation_form_class
            )
            formset = DispositionParticipationFormset(
                queryset=AbstractParticipation.objects.filter(pk=instance.pk),
                prefix="participations",
                start_index=form.cleaned_data["new_index"],
            )
            form = next(filter(lambda form: form.instance.id == instance.id, formset))
            return self.render_to_response({"form": form, "shift": shift})
        raise Http404()


class DispositionView(DispositionBaseViewMixin, TemplateView):
    template_name = "core/disposition/disposition.html"

    def get_formset(self):
        DispositionParticipationFormset = get_disposition_formset(
            self.object.signup_method.disposition_participation_form_class
        )
        formset = DispositionParticipationFormset(
            self.request.POST or None,
            queryset=self.object.participations.all(),
            prefix="participations",
        )
        return formset

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()

            for participation, changed_fields in formset.changed_objects:
                if "state" in changed_fields:
                    if participation.state == AbstractParticipation.States.CONFIRMED:
                        from ephios.core.services.notifications.types import (
                            ParticipationConfirmedNotification,
                        )

                        ParticipationConfirmedNotification.send(participation)
                    elif participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
                        from ephios.core.services.notifications.types import (
                            ParticipationRejectedNotification,
                        )

                        ParticipationRejectedNotification.send(participation)

            self.object.participations.filter(
                state=AbstractParticipation.States.GETTING_DISPATCHED
            ).delete()
            return redirect(self.object.event.get_absolute_url())
        return self.get(request, *args, **kwargs, formset=formset)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("formset", self.get_formset())
        kwargs.setdefault("states", AbstractParticipation.States)
        kwargs.setdefault(
            "participant_template",
            self.object.signup_method.disposition_participation_form_class.disposition_participation_template,
        )
        kwargs.setdefault(
            "add_user_form",
            AddUserForm(user_queryset=addable_users(self.object)),
        )
        return super().get_context_data(**kwargs)
