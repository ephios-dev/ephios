from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.timezone import get_default_timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from ephios.core.forms.events import ShiftForm
from ephios.core.models import Event, Shift
from ephios.core.signals import shift_forms
from ephios.core.signup.flow import enabled_signup_flows, signup_flow_from_slug
from ephios.core.signup.structure import enabled_shift_structures, shift_structure_from_slug
from ephios.extra.mixins import CustomPermissionRequiredMixin, PluginFormMixin


class ShiftCreateView(CustomPermissionRequiredMixin, PluginFormMixin, TemplateView):
    permission_required = "core.change_event"
    template_name = "core/shift_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.event = get_object_or_404(Event.all_objects, pk=self.kwargs.get("pk"))

    def get_permission_object(self):
        return self.event

    def get_shift_form(self):
        return ShiftForm(self.request.POST or None)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("event", self.event)
        kwargs.setdefault("form", self.get_shift_form())
        kwargs.setdefault("flow_configuration_form", "")
        kwargs.setdefault("structure_configuration_form", "")
        return super().get_context_data(**kwargs)

    def get_plugin_forms(self):
        return shift_forms.send(
            sender=None, shift=getattr(self, "object", None), request=self.request
        )

    def post(self, *args, **kwargs):
        form = self.get_shift_form()
        self.object = form.instance

        try:
            signup_flow = signup_flow_from_slug(
                self.request.POST.get("signup_flow_slug"), event=self.event
            )
            structure = shift_structure_from_slug(
                self.request.POST.get("structure_slug"),
                event=self.event,
            )
        except KeyError:
            if not list(enabled_signup_flows()):
                form.add_error(
                    "signup_flow_slug",
                    _("You must enable plugins providing signup flows to continue."),
                )
            if not list(enabled_shift_structures()):
                form.add_error(
                    "structure_slug",
                    _("You must enable plugins providing shift structures to continue."),
                )
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                )
            )
        except ValueError as e:
            form.add_error(None, ValidationError(e))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                )
            )

        flow_configuration_form = signup_flow.get_configuration_form(
            self.request.POST, event=self.event
        )
        structure_configuration_form = structure.get_configuration_form(
            self.request.POST, event=self.event
        )
        if not all(
            [
                self.is_valid(form),
                flow_configuration_form.is_valid(),
                structure_configuration_form.is_valid(),
            ]
        ):
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    flow_configuration_form=flow_configuration_form,
                    structure_configuration_form=structure_configuration_form,
                )
            )

        shift = form.save(commit=False)
        shift.event = self.event
        shift.signup_flow_configuration = flow_configuration_form.cleaned_data
        shift.structure_configuration = structure_configuration_form.cleaned_data
        shift.save()
        self.save_plugin_forms()
        if "addAnother" in self.request.POST:
            return redirect(reverse("core:event_createshift", kwargs={"pk": self.kwargs.get("pk")}))
        try:
            self.event.activate()
            messages.success(
                self.request,
                _("The event {title} has been saved.").format(title=self.event.title),
            )
        except ValidationError as e:
            messages.error(self.request, e)
        return redirect(self.event.get_absolute_url())


class AbstractShiftConfigurationFormView(CustomPermissionRequiredMixin, SingleObjectMixin, View):
    queryset = Event.all_objects
    permission_required = "core.change_event"
    pk_url_kwarg = "event_id"

    def get(self, request, *args, **kwargs):
        try:
            shift = self.get_object().shifts.get(pk=request.GET.get("shift_id") or None)
        except Shift.DoesNotExist:
            shift = None
        form = self.get_form(self.get_object(), shift)
        return render(
            request,
            "core/fragments/shift_signup_config_form.html",
            {
                "form": form,
            },
        )

    def get_form(self, event, shift=None):
        raise NotImplementedError


class SignupFlowConfigurationFormView(AbstractShiftConfigurationFormView):
    def get_form(self, event, shift=None):
        return signup_flow_from_slug(
            self.kwargs.get("slug"), event=event, shift=shift
        ).get_configuration_form()


class ShiftStructureConfigurationFormView(AbstractShiftConfigurationFormView):
    def get_form(self, event, shift=None):
        return shift_structure_from_slug(
            self.kwargs.get("slug"), event=event, shift=shift
        ).get_configuration_form()


class ShiftUpdateView(
    CustomPermissionRequiredMixin, PluginFormMixin, SingleObjectMixin, TemplateView
):
    model = Shift
    template_name = "core/shift_form.html"
    permission_required = "core.change_event"

    def get_permission_object(self):
        return self.get_object().event

    def get_shift_form(self):
        return ShiftForm(
            self.request.POST or None,
            instance=self.object,
            initial={
                "date": self.object.meeting_time.date(),
                "meeting_time": self.object.meeting_time.astimezone(get_default_timezone()).time(),
                "start_time": self.object.start_time.astimezone(get_default_timezone()).time(),
                "end_time": self.object.end_time.astimezone(get_default_timezone()).time(),
            },
        )

    def get_flow_configuration_form(self):
        return self.object.signup_flow.get_configuration_form(data=self.request.POST or None)

    def get_structure_configuration_form(self):
        return self.object.structure.get_configuration_form(data=self.request.POST or None)

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.setdefault("event", self.object.event)
        kwargs.setdefault("form", self.get_shift_form())
        kwargs.setdefault("flow_configuration_form", self.get_flow_configuration_form())
        kwargs.setdefault("structure_configuration_form", self.get_structure_configuration_form())
        return super().get_context_data(**kwargs)

    def get_plugin_forms(self):
        return shift_forms.send(sender=None, shift=self.object, request=self.request)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_shift_form()
        flow_configuration_form = self.get_flow_configuration_form()
        structure_configuration_form = self.get_structure_configuration_form()
        try:
            signup_flow = signup_flow_from_slug(
                self.request.POST["signup_flow_slug"], shift=self.object
            )
            flow_configuration_form = signup_flow.get_configuration_form(
                self.request.POST, event=self.object.event
            )
            structure = shift_structure_from_slug(
                self.request.POST["structure_slug"], shift=self.object
            )
            structure_configuration_form = structure.get_configuration_form(
                self.request.POST, event=self.object.event
            )
        except (ValueError, MultiValueDictKeyError):
            pass
        else:
            if all(
                [
                    self.is_valid(form),
                    flow_configuration_form.is_valid(),
                    structure_configuration_form.is_valid(),
                ]
            ):
                shift = form.save(commit=False)
                shift.signup_flow_configuration = flow_configuration_form.cleaned_data
                shift.structure_configuration = structure_configuration_form.cleaned_data
                shift.save()
                self.save_plugin_forms()
                if "addAnother" in self.request.POST:
                    return redirect(
                        reverse("core:event_createshift", kwargs={"pk": shift.event.pk})
                    )
                messages.success(
                    self.request, _("The shift {shift} has been saved.").format(shift=shift)
                )
                return redirect(self.object.event.get_absolute_url())

        return self.render_to_response(
            self.get_context_data(
                form=form,
                flow_configuration_form=flow_configuration_form,
                structure_configuration_form=structure_configuration_form,
            )
        )


class ShiftDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "core.change_event"
    model = Shift

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def form_valid(self, form):
        if self.object.event.shifts.count() == 1:
            messages.error(self.request, _("You cannot delete the last shift!"))
            return redirect(self.object.event.get_absolute_url())
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, _("The shift has been deleted."))
        return self.object.event.get_absolute_url()

    def get_permission_object(self):
        return self.object.event
