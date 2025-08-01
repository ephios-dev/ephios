from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.questionnaires.models import Question, Questionnaire, SavedAnswer


class ChoiceForm(forms.Form):
    name = forms.CharField(
        label=_("Choice name"),
        max_length=100,
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


class QuestionArchiveForm(forms.ModelForm):
    archived = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Question
        fields = ["archived"]

    def __init__(self, *args, set_archived: bool, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_archived = set_archived

    def get_initial_for_field(self, field, field_name):
        if field_name == "archived":
            return self.set_archived

        return super().get_initial_for_field(field, field_name)


class QuestionnaireForm(BasePluginFormMixin, forms.ModelForm):
    questions = forms.ModelMultipleChoiceField(
        queryset=Question.objects.filter(archived=False), widget=Select2MultipleWidget
    )

    class Meta:
        model = Questionnaire
        fields = ["questions"]

    def __init__(self, *args, shift, **kwargs):
        kwargs.setdefault("prefix", "questionnaires")
        self.shift = shift
        try:
            kwargs.setdefault("instance", Questionnaire.objects.get(shift_id=shift.id))
        except (AttributeError, Questionnaire.DoesNotExist):
            pass
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["questions"].queryset = Question.objects.filter(
                Q(archived=False) | Q(pk__in=self.instance.questions.values_list("pk", flat=True))
            )

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


class SavedAnswerForm(forms.ModelForm):
    class Meta:
        model = SavedAnswer
        fields = ["answer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["answer"] = self.instance.question.get_saved_answer_form_field()
