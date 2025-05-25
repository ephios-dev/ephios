from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.plugins.questionnaires.models import Question


class ChoiceForm(forms.Form):
    name = forms.CharField(label=_("Choice name"))


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
