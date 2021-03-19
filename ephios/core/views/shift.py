from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import get_default_timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DeleteView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from ephios.core import signup
from ephios.core.forms.events import ShiftForm
from ephios.core.models import Event, Shift
from ephios.extra.mixins import CustomPermissionRequiredMixin


class ShiftCreateView(CustomPermissionRequiredMixin, TemplateView):
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
        kwargs.setdefault("configuration_form", "")
        return super().get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        form = self.get_shift_form()
        try:
            from ephios.core.signup import signup_method_from_slug

            signup_method = signup_method_from_slug(self.request.POST["signup_method_slug"])
        except KeyError as e:
            if not list(signup.enabled_signup_methods()):
                form.add_error(
                    "signup_method_slug",
                    _("You must enable plugins providing signup methods to continue."),
                )
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                )
            )
        except ValueError as e:
            raise ValidationError(e) from e
        else:
            configuration_form = signup_method.get_configuration_form(self.request.POST)
            if not all((form.is_valid(), configuration_form.is_valid())):
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        configuration_form=signup_method.render_configuration_form(
                            form=configuration_form
                        ),
                    )
                )

            shift = form.save(commit=False)
            shift.event = self.event
            shift.signup_configuration = configuration_form.cleaned_data
            shift.save()
            if "addAnother" in self.request.POST:
                return redirect(
                    reverse("core:event_createshift", kwargs={"pk": self.kwargs.get("pk")})
                )
            try:
                self.event.activate()
                messages.success(
                    self.request,
                    _("The event {title} has been saved.").format(title=self.event.title),
                )
            except ValidationError as e:
                messages.error(self.request, e)
            return redirect(self.event.get_absolute_url())


class ShiftConfigurationFormView(View):
    def get(self, request, *args, **kwargs):
        from ephios.core.signup import signup_method_from_slug

        signup_method = signup_method_from_slug(self.kwargs.get("slug"))
        return HttpResponse(signup_method.render_configuration_form())


class ShiftUpdateView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
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

    def get_configuration_form(self):
        return self.object.signup_method.render_configuration_form(data=self.request.POST or None)

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.setdefault("event", self.object.event)
        kwargs.setdefault("form", self.get_shift_form())
        kwargs.setdefault("configuration_form", self.get_configuration_form())
        return super().get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_shift_form()
        try:
            from ephios.core.signup import signup_method_from_slug

            signup_method = signup_method_from_slug(self.request.POST["signup_method_slug"])
            configuration_form = signup_method.get_configuration_form(self.request.POST)
        except ValueError as e:
            raise ValidationError(e) from e
        if form.is_valid() and configuration_form.is_valid():
            shift = form.save(commit=False)
            shift.signup_configuration = configuration_form.cleaned_data
            shift.save()
            if "addAnother" in self.request.POST:
                return redirect(reverse("core:event_createshift", kwargs={"pk": shift.event.pk}))
            messages.success(
                self.request, _("The shift {shift} has been saved.").format(shift=shift)
            )
            return redirect(self.object.event.get_absolute_url())
        return self.render_to_response(
            self.get_context_data(
                form=form,
                configuration_form=signup_method.render_configuration_form(form=configuration_form),
            )
        )


class ShiftDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "core.change_event"
    model = Shift

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def delete(self, request, *args, **kwargs):
        if self.object.event.shifts.count() == 1:
            messages.error(self.request, _("You cannot delete the last shift!"))
            return redirect(self.object.event.get_absolute_url())
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, _("The shift has been deleted."))
        return self.object.event.get_absolute_url()

    def get_permission_object(self):
        return self.object.event
