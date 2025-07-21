from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.questionnaires.models import Answer, Question, Questionnaire


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


class QuestionnaireForm(BasePluginFormMixin, forms.ModelForm):
    class Meta:
        model = Questionnaire
        fields = ["questions"]
        widgets = {"questions": Select2MultipleWidget}

    def __init__(self, *args, shift, **kwargs):
        kwargs.setdefault("prefix", "questionnaires")
        self.shift = shift
        try:
            kwargs.setdefault("instance", Questionnaire.objects.get(shift_id=shift.id))
        except (AttributeError, Questionnaire.DoesNotExist):
            pass
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        if self.cleaned_data.get("questions"):
            self.instance.shift = self.shift
            super().save(commit)
        elif self.instance.pk:
            self.instance.delete()

    @property
    def heading(self):
        return _("Questionnaire")

    def is_function_active(self):
        return self.instance.pk and self.instance.questions.count() > 0
