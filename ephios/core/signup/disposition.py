from django import forms
from django.http import Http404
from django.shortcuts import redirect
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2Widget

from ephios.core.models import (
    AbstractParticipation,
    LocalParticipation,
    Qualification,
    Shift,
    UserProfile,
)
from ephios.core.services.notifications.types import (
    ParticipationCustomizationNotification,
    ParticipationStateChangeNotification,
    ResponsibleParticipationStateChangeNotification,
)
from ephios.core.signup.forms import BaseParticipationForm
from ephios.extra.mixins import CustomPermissionRequiredMixin


class MissingParticipation(ValueError):
    pass


class BaseDispositionParticipationForm(BaseParticipationForm):
    disposition_participation_template = "core/disposition/fragment_participation.html"

    def __init__(self, **kwargs):
        try:
            self.shift = kwargs["instance"].shift
        except (AttributeError, KeyError) as e:
            raise MissingParticipation("an instance must be provided") from e

        super().__init__(**kwargs)
        self.can_delete = self.instance.state == AbstractParticipation.States.GETTING_DISPATCHED
        self.fields["comment"].disabled = True

    class Meta(BaseParticipationForm.Meta):
        fields = ["state", "individual_start_time", "individual_end_time", "comment"]
        widgets = {"state": forms.HiddenInput(attrs={"class": "state-input"})}


class DispositionBaseModelFormset(forms.BaseModelFormSet):
    """
    To allow us to dynamically add server-side rendered forms to a formset
    we patch a way to change the starting index.
    """

    def __init__(self, *args, start_index=0, **kwargs):
        self._start_index = start_index
        super().__init__(*args, **kwargs)

    @cached_property
    def forms(self):
        """
        This formset is meant to only work with existing participation objects.
        If a user submits a formset including a form for a deleted participation
        (e.g. due to getting dispatched being deleted), we need to not include them.
        BaseDispositionParticipationForm raises MissingParticipation if instantiated
        without an instance.
        """
        # taken from super().forms
        forms_with_instance = []
        for i in range(self.total_form_count()):
            try:
                forms_with_instance.append(self._construct_form(i, **self.get_form_kwargs(i)))
            except MissingParticipation:
                pass
        return forms_with_instance

    def add_prefix(self, index):
        return f"{self.prefix}-{self._start_index + index}"

    def save_existing(self, form, obj, commit=True):
        """Existing participation state overwrites the getting dispatched state."""
        if form.instance.state == AbstractParticipation.States.GETTING_DISPATCHED:
            form.instance.state = AbstractParticipation.objects.get(id=form.instance.id).state
        return form.save(commit=commit)


def get_disposition_formset(form):
    return forms.modelformset_factory(
        model=AbstractParticipation,
        formset=DispositionBaseModelFormset,
        form=form,
        extra=0,
        edit_only=True,
        can_order=False,
        can_delete=True,
    )


def addable_users(shift):
    """
    Return queryset of user objects that can be added to the shift.
    This also includes users that already have a participation, as that might have gotten removed in JS.

    This also includes users that can normally not see the event. The permission will be added accordingly.
    If needed, this method could be moved to signup flows.
    """
    return UserProfile.objects.all()


class AddUserForm(forms.Form):
    user = forms.ModelChoiceField(
        widget=ModelSelect2Widget(
            model=UserProfile,
            search_fields=["display_name__icontains"],
            attrs={
                "form": "add-user-form",
                "data-placeholder": _("search"),
                "data-tags": "true",
                "data-token-separators": [],
            },
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

    def get_permission_object(self):
        return self.object.event


class AddUserView(DispositionBaseViewMixin, TemplateResponseMixin, View):
    def get_template_names(self):
        return [
            self.object.structure.disposition_participation_form_class.disposition_participation_template
        ]

    def post(self, request, *args, **kwargs):
        shift = self.object
        form = AddUserForm(
            data=request.POST,
            user_queryset=addable_users(shift),
        )
        if form.is_valid():
            user: UserProfile = form.cleaned_data["user"]
            instance = shift.signup_flow.get_or_create_participation_for(user.as_participant())
            instance.state = AbstractParticipation.States.GETTING_DISPATCHED
            instance.save()

            DispositionParticipationFormset = get_disposition_formset(
                self.object.structure.disposition_participation_form_class
            )
            formset = DispositionParticipationFormset(
                queryset=AbstractParticipation.objects.filter(pk=instance.pk),
                prefix="participations",
                start_index=form.cleaned_data["new_index"],
            )
            form = next(filter(lambda form: form.instance.id == instance.id, formset))
            return self.render_to_response({"form": form, "shift": shift})
        raise Http404()


class AddPlaceholderParticipantView(DispositionBaseViewMixin, TemplateResponseMixin, View):
    def get_template_names(self):
        return [
            self.object.structure.disposition_participation_form_class.disposition_participation_template
        ]

    def post(self, request, *args, **kwargs):
        shift = self.object
        from ephios.core.signup.participants import PlaceholderParticipant

        participant = PlaceholderParticipant(
            display_name=request.POST["display_name"],
            qualifications=Qualification.objects.none(),
            email=None,
            date_of_birth=None,
        )
        instance = shift.signup_flow.get_or_create_participation_for(participant)
        instance.state = AbstractParticipation.States.GETTING_DISPATCHED
        instance.save()

        DispositionParticipationFormset = get_disposition_formset(
            self.object.structure.disposition_participation_form_class
        )
        formset = DispositionParticipationFormset(
            queryset=AbstractParticipation.objects.filter(pk=instance.pk),
            prefix="participations",
            start_index=int(request.POST["new_index"]),
        )
        form = next(filter(lambda form: form.instance.id == instance.id, formset))
        return self.render_to_response({"form": form, "shift": shift})


class DispositionView(DispositionBaseViewMixin, TemplateView):
    template_name = "core/disposition/disposition.html"

    def get_formset(self):
        DispositionParticipationFormset = get_disposition_formset(
            self.object.structure.disposition_participation_form_class
        )
        formset = DispositionParticipationFormset(
            self.request.POST or None,
            queryset=self.object.participations.all(),
            prefix="participations",
        )
        return formset

    def _send_participant_notifications(self, formset):
        for participation, changed_fields in formset.changed_objects:
            if (
                participation.get_real_instance_class() != LocalParticipation
                or participation.user != self.request.user
            ):
                if "state" in changed_fields:
                    ParticipationStateChangeNotification.send(
                        participation, acting_user=self.request.user
                    )
                    ResponsibleParticipationStateChangeNotification.send(
                        participation, acting_user=self.request.user
                    )
                elif participation.state == AbstractParticipation.States.CONFIRMED:
                    form: BaseParticipationForm = next(
                        filter(lambda f, p=participation: f.instance == p, formset.forms)
                    )
                    if claims := form.get_customization_notification_info():
                        # If state didn't change, but confirmed participation was customized, notify about that.
                        ParticipationCustomizationNotification.send(participation, claims)

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if not formset.is_valid():
            return self.get(request, *args, **kwargs, formset=formset)

        formset.save()
        self._send_participant_notifications(formset)

        # non_polymorphic() needed because of https://github.com/django-polymorphic/django-polymorphic/issues/34
        self.object.participations.filter(
            state=AbstractParticipation.States.GETTING_DISPATCHED
        ).non_polymorphic().delete()
        return redirect(self.object.event.get_absolute_url())

    def get_context_data(self, **kwargs):
        kwargs.setdefault("formset", self.get_formset())
        kwargs.setdefault("states", AbstractParticipation.States)
        kwargs.setdefault(
            "participant_template",
            self.object.structure.disposition_participation_form_class.disposition_participation_template,
        )
        kwargs.setdefault(
            "render_requested_state",
            self.object.signup_flow.uses_requested_state
            or self.object.participations.filter(
                state=AbstractParticipation.States.REQUESTED
            ).exists(),
        )
        kwargs.setdefault(
            "add_user_form",
            AddUserForm(user_queryset=addable_users(self.object)),
        )
        return super().get_context_data(**kwargs)
