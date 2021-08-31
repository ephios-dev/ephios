from django import forms
from django.contrib import messages
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.views.generic import CreateView, FormView, ListView, UpdateView
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import Qualification, QualificationGrant
from ephios.core.views.settings import SettingsViewMixin
from ephios.extra.mixins import StaffRequiredMixin

# Templates in this plugin are under core/, because Qualification is a core model.
from ephios.plugins.qualification_management.importing import (
    QualificationChangeManager,
    QualificationImportForm,
)


class QualificationListView(StaffRequiredMixin, SettingsViewMixin, ListView):
    model = Qualification
    ordering = ("category__title", "title")


class QualificationImportView(StaffRequiredMixin, SettingsViewMixin, FormView):
    template_name = "core/import.html"
    form_class = QualificationImportForm

    def get_success_url(self):
        return reverse("qualification_management:settings_qualification_list")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ["title", "uuid", "abbreviation", "category", "included_qualifications"]
        widgets = {"included_qualifications": Select2MultipleWidget}
        help_texts = {
            "uuid": _(
                "Used to identify qualifications accross the ephios ecosystem. Only change if you know what you are doing."
            )
        }


class QualificationCreateView(StaffRequiredMixin, SettingsViewMixin, CreateView):
    model = Qualification
    form_class = QualificationForm

    def get_success_url(self):
        messages.success(self.request, _("Qualification was saved."))
        return reverse("qualification_management:settings_qualification_list")


class QualificationUpdateView(StaffRequiredMixin, SettingsViewMixin, UpdateView):
    model = Qualification
    form_class = QualificationForm

    def get_success_url(self):
        messages.success(self.request, _("Qualification was saved."))
        return reverse("qualification_management:settings_qualification_list")


class QualificationDeleteForm(forms.Form):
    fix_inclusions = forms.BooleanField(
        label=_("Maintain transitive inclusion"),
        initial=True,
        required=False,
    )
    move_grants_to_other_qualification = forms.ModelMultipleChoiceField(
        label=_("Migrate users to other qualification"),
        required=False,
        widget=Select2MultipleWidget,
        queryset=Qualification.objects.none(),
    )

    @cached_property
    def _active_grants(self):
        return self.qualification.grants.exclude(expires__isnull=False, expires__lt=now())

    def __init__(self, *args, **kwargs):
        self.qualification = kwargs.pop("instance")
        super().__init__(*args, **kwargs)
        self.fields["fix_inclusions"].help_text = _(
            "If checked, superior qualifications ({superior}) will include inferior ({inferior}) qualifications."
        ).format(
            superior=", ".join(map(str, self.qualification.included_by.all())) or _("none"),
            inferior=", ".join(map(str, self.qualification.included_qualifications.all()))
            or _("none"),
        )

        self.fields["move_grants_to_other_qualification"].queryset = Qualification.objects.exclude(
            pk=self.qualification.pk
        )
        help_text = _(
            "Select qualifications to apply to users with the qualification about to be deleted. Expiration dates will be kept."
        )

        if count := self._active_grants.count():
            help_text += " "
            help_text += ngettext(
                "There is {count} user with this qualification.",
                "There are {count} users with this qualification.",
                count,
            ).format(count=count)

        self.fields["move_grants_to_other_qualification"].help_text = help_text

    def _move_users_to_other_qualifications(self):
        new_grants = []
        for new_qualification in self.cleaned_data["move_grants_to_other_qualification"]:
            for old_grant in self._active_grants:
                new_grants.append(
                    QualificationGrant(
                        user_id=old_grant.user_id,
                        qualification_id=new_qualification.id,
                        expires=old_grant.expires,
                    )
                )
        QualificationGrant.objects.bulk_create(new_grants)

    def save(self):
        assert self.is_valid()
        self._move_users_to_other_qualifications()
        if self.cleaned_data["fix_inclusions"]:
            manager = QualificationChangeManager()
            manager.remove_qualifications_from_db_fixing_inclusion(self.qualification)
            manager.commit()
        else:
            self.qualification.delete()


class QualificationDeleteView(StaffRequiredMixin, SettingsViewMixin, UpdateView):
    model = Qualification
    form_class = QualificationDeleteForm
    template_name_suffix = "_confirm_delete"

    def get_success_url(self):
        messages.info(self.request, _("Qualification was deleted."))
        return reverse("qualification_management:settings_qualification_list")
