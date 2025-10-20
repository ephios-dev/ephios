from django import forms
from django.db import models
from django.utils.html import escape, format_html
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget, Select2Widget
from rest_framework import serializers

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.core.models.users import UserProfile
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant
from ephios.modellogging.log import ModelFieldsLogConfig, dont_log, log


@log()
class Question(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", _("Text input")
        SINGLE = "single", _("Single choice")
        MULTIPLE = "multiple", _("Multiple choice")

    name = models.CharField(
        max_length=50,
        verbose_name=_("Name"),
        help_text=_(
            "The name of the question is used to identify the question, for example when picking questions for a shift"
        ),
    )
    question_text = models.CharField(max_length=250, verbose_name=_("Question"))
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    required = models.BooleanField(
        verbose_name=_("Required"),
        help_text=_("Whether users must submit an answer to this question"),
    )
    type = models.CharField(
        max_length=20, verbose_name=_("Type"), choices=Type.choices, default=Type.TEXT
    )
    choices = models.JSONField(default=list, verbose_name=_("Choices"))
    archived = models.BooleanField(
        default=False,
        verbose_name=_("Archived"),
        help_text=_(
            "Archive a question to hide it in the question selection for new shifts without affecting shifts where this question is already in use."
        ),
    )
    use_saved_answers = models.BooleanField(
        verbose_name=_("Use saved answers"),
        help_text=_(
            "If checked, forms will be prefilled with a users saved answer to this question, if available. "
            "Enable this if answers are independent of the event the question is used for."
        ),
        default=False,
    )

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self):
        return str(self.name)

    def can_delete(self):
        return not self.questionnaire_set.exists() and not self.answer_set.exists()

    def _get_field_classes(self):
        match self.type:
            case self.Type.TEXT:
                return forms.CharField, serializers.CharField
            case self.Type.SINGLE:
                return forms.ChoiceField, serializers.ChoiceField
            case self.Type.MULTIPLE:
                return forms.MultipleChoiceField, serializers.MultipleChoiceField

    def _get_field_kwargs(self):
        form_kwargs = {}
        serializer_kwargs = {}

        match self.type:
            case self.Type.TEXT:
                max_length = 100
                form_kwargs["max_length"] = max_length
                serializer_kwargs["max_length"] = max_length
            case self.Type.SINGLE:
                form_kwargs["widget"] = (
                    forms.RadioSelect if len(self.choices) <= 5 else Select2Widget
                )
            case self.Type.MULTIPLE:
                form_kwargs["widget"] = Select2MultipleWidget

        if self.type != self.Type.TEXT:
            assert isinstance(
                self.choices, list
            ), f"The choices of question {self.name} are not a list"
            # We're intentionally using the plain `choice` as choice key and don't convert it into a slug or similar.
            # This is uncommon but seems to be the best solution with choices from (potentially changing) user input
            # pylint: disable=not-an-iterable
            choices = [(choice, choice) for choice in self.choices]
            form_kwargs["choices"] = choices
            serializer_kwargs["choices"] = choices

        # show an icon in forms indicating the answer can be saved
        if self.use_saved_answers:
            form_kwargs["help_text"] = format_html(
                (
                    '{description}<br/><i class="fas fa-info-circle"></i> {infotext}'
                    if self.description
                    else '<i class="fas fa-info-circle"></i> {infotext}'
                ),
                description=self.description,
                infotext=_("Answer can be saved to your profile."),
            )

        return form_kwargs, serializer_kwargs

    def _get_initial_answer(
        self, participant: AbstractParticipant, participation: AbstractParticipation
    ):
        """
        Restores answer from participation (when editing) or the user's saved answers (if local participant)
        """
        initial = None
        if existing_answer := Answer.objects.filter(
            participation_id=participation.pk, question=self
        ).first():
            initial = existing_answer.answer
        elif self.use_saved_answers and (
            saved_answer := (
                SavedAnswer.objects.filter(user=participant.user, question=self).first()
                if isinstance(participant, LocalUserParticipant)
                else None
            )
        ):
            initial = saved_answer.answer

        # Reset answer it does not match the question type
        match self.type:
            case self.Type.TEXT:
                if isinstance(initial, list):
                    # Convert multiple answers if the question was a multiple choice question before
                    initial = ", ".join(initial)
            case self.Type.SINGLE:
                if isinstance(initial, list):
                    # Reset answer if the question was a multiple choice question before
                    if len(initial) == 1:
                        initial = initial[0]
                    else:
                        initial = None

                if initial not in self.choices:
                    # Reset answer if the option does not exist any more
                    initial = None
            case self.Type.MULTIPLE:
                if isinstance(initial, str):
                    # Convert single answer to multi-answer
                    initial = [initial]

                if isinstance(initial, list):
                    # Remove invalid answers if answers are set
                    initial = [answer for answer in initial if answer in self.choices]

        return initial

    def get_signup_form_field(
        self, participant: AbstractParticipant, participation: AbstractParticipation
    ):
        initial = self._get_initial_answer(participant, participation)

        field_name = self.get_form_slug()

        field_classes = self._get_field_classes()
        field_kwargs = self._get_field_kwargs()

        field = {
            "label": escape(self.question_text),
            "help_text": escape(self.description),
            "default": initial,
            "required": self.required,
            "form_class": field_classes[0],
            "form_kwargs": {
                **field_kwargs[0],
            },
            "serializer_class": field_classes[1],
            "serializer_kwargs": {
                **field_kwargs[1],
            },
        }

        return field_name, field

    def get_saved_answer_form_field(self):
        field_class = self._get_field_classes()[0]
        field_kwargs = self._get_field_kwargs()[0]

        field_kwargs["label"] = _("Answer")

        return field_class(**field_kwargs)

    def get_form_slug(self):
        return "questionnaires_" + slugify(f"{self.pk} {self.name}")

    @staticmethod
    def get_pk_from_slug(slug: str):
        """
        Returns the questions' pk from a form field slug  generated by `Question.get_form_slug`.
        These slugs have the format `questionnaires_123-demo-question`.

        For this slug, this method would return `123`.
        """
        return int(slug.split("_", maxsplit=1)[1].split("-")[0])


@log(
    ModelFieldsLogConfig(attach_to_func=lambda questionnaire: (Shift, questionnaire.shift_id)),
)
class Questionnaire(models.Model):
    shift = models.OneToOneField(Shift, on_delete=models.CASCADE)
    questions = models.ManyToManyField(Question, blank=True)

    class Meta:
        verbose_name = _("Questionnaire")
        verbose_name_plural = _("Questionnaires")

    def __str__(self):
        return f'{", ".join(self.questions.values_list("name", flat=True))} @ {self.shift}'


def answer_text(answer):
    return ", ".join(answer) if isinstance(answer, list) else answer


@log(
    ModelFieldsLogConfig(
        attach_to_func=lambda answer: (AbstractParticipation, answer.participation_id)
    ),
)
class Answer(models.Model):
    participation = models.ForeignKey(AbstractParticipation, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.JSONField(verbose_name=_("Answer"))

    class Meta:
        verbose_name = _("Answer")
        verbose_name_plural = _("Answers")

    def __str__(self):
        return f'{self.question}: "{self.answer}" ({self.participation})'

    @property
    def answer_text(self):
        return answer_text(self.answer)


@dont_log
class SavedAnswer(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.JSONField(verbose_name=_("Answer"))

    class Meta:
        verbose_name = _("Saved answer")
        verbose_name_plural = _("Saved answers")

    def __str__(self):
        return f'{self.question}: "{self.answer}" ({self.user})'

    @property
    def answer_text(self):
        return answer_text(self.answer)
