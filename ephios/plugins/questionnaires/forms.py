from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.questionnaires.models import Answer, Question


class ChoiceForm(forms.Form):
    name = forms.CharField(
        label=_("Choice name"),
        # pylint: disable=protected-access
        max_length=Answer._meta.get_field("answer").max_length,
    )


ChoicesFormset = forms.formset_factory(ChoiceForm, can_delete=True, extra=2)


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["name", "question_text", "description", "required", "type"]

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.choices = ChoicesFormset(
            initial=[{"name": choice} for choice in self.instance.choices],
            data=data,
            prefix="choices",
        )

    def save(self, commit=True):
        self.instance.choices = [
            choice["name"]
            for choice in self.choices.cleaned_data
            if "name" in choice and not choice["DELETE"]
        ]
        return super().save(commit)


class QuestionnaireForm(BasePluginFormMixin, forms.Form):
    questions = forms.ModelMultipleChoiceField(
        queryset=Question.objects.all(), widget=Select2MultipleWidget, required=False
    )

    def __init__(self, *args, shift, **kwargs):
        kwargs.setdefault("prefix", "questionnaires")
        super().__init__(*args, **kwargs)
        self.shift = shift
        self.fields["questions"].initial = Question.objects.filter(pk__in=self.shift.questionnaire)

    def save(self):
        self.shift.questionnaire = [
            question.pk for question in self.cleaned_data["questions"].all()
        ]
        self.shift.save()

    @property
    def heading(self):
        return _("Questionnaire")

    def is_function_active(self):
        return bool(len(self.shift.questionnaire) > 0)
