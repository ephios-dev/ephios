from django import forms
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from django_select2.forms import ModelSelect2Widget

from ephios.event_management.models import AbstractParticipation, Shift
from ephios.extra.permissions import CustomPermissionRequiredMixin
from ephios.user_management.models import UserProfile


class BaseDispositionParticipationForm(forms.ModelForm):
    disposition_participation_template = "basesignup/common/fragment_participant.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.shift = self.instance.shift
        except AttributeError:
            raise ValueError(f"{type(self)} must be initialized with an instance.")

    class Meta:
        model = AbstractParticipation
        fields = ["state"]
        widgets = dict(state=forms.HiddenInput(attrs={"class": "state-input"}))


def get_disposition_formset(form):
    return forms.modelformset_factory(
        model=AbstractParticipation,
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
    # TODO: check how that looks and wether we actually check for that elsewhere and also actually add the permission.
    """
    return UserProfile.objects.all()  # you surprised it's just this? :D


class AddUserForm(forms.Form):
    user = forms.ModelChoiceField(
        widget=ModelSelect2Widget(
            model=UserProfile,
            search_fields=["first_name__icontains", "last_name__icontains"],
            attrs={"form": "add-user-form"},
        ),
        queryset=UserProfile.objects.none(),  # set using __init__
    )

    def __init__(self, user_queryset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = user_queryset


class DispositionBaseViewMixin(CustomPermissionRequiredMixin, SingleObjectMixin):
    permission_required = "event_management.change_event"
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
            user_queryset=addable_users(shift),
            data=request.POST,
        )
        if form.is_valid():
            user: UserProfile = form.cleaned_data["user"]
            instance = shift.signup_method.get_participation_for(user.as_participant())
            instance.state = AbstractParticipation.States.RESPONSIBLE_ADDED
            instance.save()

            DispositionParticipationFormset = get_disposition_formset(
                self.object.signup_method.disposition_participation_form_class
            )
            formset = DispositionParticipationFormset(
                queryset=self.object.participations,
                prefix="participations",
            )
            form = next(filter(lambda form: form.instance.id == instance.id, formset))
            return self.render_to_response({"form": form})
        raise Http404("User does not exist")


class DispositionView(DispositionBaseViewMixin, TemplateView):
    template_name = "basesignup/common/disposition.html"

    def get_formset(self):
        DispositionParticipationFormset = get_disposition_formset(
            self.object.signup_method.disposition_participation_form_class
        )
        formset = DispositionParticipationFormset(
            self.request.POST or None,
            queryset=self.object.participations,
            prefix="participations",
        )
        return formset

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()
            self.object.participations.filter(
                state=AbstractParticipation.States.RESPONSIBLE_ADDED
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
