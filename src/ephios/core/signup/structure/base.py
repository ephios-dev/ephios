import logging
from argparse import Namespace
from collections import OrderedDict
from operator import attrgetter

from django.template.loader import get_template

from ephios.core.models import AbstractParticipation
from ephios.core.signup.disposition import BaseDispositionParticipationForm
from ephios.core.signup.forms import SignupConfigurationForm
from ephios.core.signup.stats import SignupStats
from ephios.core.signup.structure.abstract import AbstractShiftStructure
from ephios.extra.utils import format_anything

logger = logging.getLogger(__name__)


class BaseShiftStructure(AbstractShiftStructure):
    """
    Shift structure with some base implementations for common methods.
    """

    @property
    def disposition_participation_form_class(self):
        return BaseDispositionParticipationForm

    @property
    def configuration_form_class(self):
        return SignupConfigurationForm

    @property
    def shift_state_template_name(self):
        raise NotImplementedError()

    def get_signup_form_fields(self, participant, participation, signup_choice):
        return {}

    def get_participant_count_bounds(self):
        return None, None

    def get_signup_stats(self) -> "SignupStats":
        min_count, max_count = self.get_participant_count_bounds()
        participations = list(self.shift.participations.all())
        confirmed_count = sum(
            p.state == AbstractParticipation.States.CONFIRMED for p in participations
        )
        return SignupStats(
            requested_count=sum(
                p.state == AbstractParticipation.States.REQUESTED for p in participations
            ),
            confirmed_count=confirmed_count,
            missing=max(min_count - confirmed_count, 0) if min_count else 0,
            free=max(max_count - confirmed_count, 0) if max_count else None,
            min_count=min_count,
            max_count=max_count,
        )

    def get_signup_info(self):
        """
        Return key/value pairs about the configuration to show in exports etc.
        """
        form_class = self.configuration_form_class
        return OrderedDict({
            label: getattr(form_class, f"format_{name}", format_anything)(value)
            for name, field in form_class.base_fields.items()
            if (label := field.label) and (value := getattr(self.configuration, name))
        })

    def get_checkers(self):
        return []

    def render(self, context):
        try:
            with context.update(self.get_shift_state_context_data(context.request)):
                return get_template(self.shift_state_template_name).template.render(context)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Shift #{self.shift.pk} state render failed")
            with context.update({"exception_message": getattr(e, "message", None)}):
                return get_template(
                    "core/fragments/shift_structure_render_error.html"
                ).template.render(context)

    def get_shift_state_context_data(self, request, **kwargs):
        """
        Additionally to the context of the event detail view, provide context for rendering `shift_state_template_name`.
        """
        kwargs["shift"] = self.shift
        kwargs["participations"] = [
            p
            for p in sorted(self.shift.participations.all(), key=attrgetter("state"), reverse=True)
            if p.state
            in {AbstractParticipation.States.REQUESTED, AbstractParticipation.States.CONFIRMED}
        ]
        kwargs["show_comments"] = request.user.has_perm("core.change_event", obj=self.shift.event)
        return kwargs

    def get_list_export_data(self):
        return [
            {
                "participation": participation,
                "required_qualifications": [],
                "description": "",
            }
            for participation in self.shift.participations.all()
        ]

    def get_configuration_form(self, *args, **kwargs):
        if self.shift is not None:
            kwargs.setdefault("initial", self.configuration.__dict__)
        kwargs.setdefault("event", self.event)
        kwargs.setdefault("shift", self.shift)
        kwargs.setdefault("description", self.description)
        form = self.configuration_form_class(*args, **kwargs)
        return form

    def __init__(self, shift, event=None):
        super().__init__(shift, event)
        self.configuration = Namespace(**{
            name: field.initial for name, field in self.configuration_form_class.base_fields.items()
        })
        if shift is not None:
            for key, value in shift.structure_configuration.items():
                setattr(self.configuration, key, value)
