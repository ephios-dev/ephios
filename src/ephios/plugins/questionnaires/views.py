from collections import Counter

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from guardian.mixins import LoginRequiredMixin

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.core.signup.disposition import DispositionBaseViewMixin
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.questionnaires.forms import QuestionArchiveForm, QuestionForm, SavedAnswerForm
from ephios.plugins.questionnaires.models import Answer, Question, SavedAnswer


class QuestionListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "questionnaires.view_question"
    model = Question
    ordering = ("name", "question_text")

    show_archived = False

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(archived=self.show_archived)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_archived"] = self.show_archived
        return context


class QuestionCreateView(CustomPermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "questionnaires.add_question"
    accept_object_perms = False
    model = Question
    form_class = QuestionForm
    template_name = "questionnaires/question_form.html"
    success_url = reverse_lazy("questionnaires:question_list")
    success_message = _("Question created successfully.")


class QuestionUpdateView(CustomPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "questionnaires.change_question"
    model = Question
    form_class = QuestionForm
    success_url = reverse_lazy("questionnaires:question_list")
    success_message = _("Question updated successfully.")


class QuestionArchiveView(CustomPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "questionnaires.change_question"
    model = Question
    form_class = QuestionArchiveForm
    template_name_suffix = "_confirm_archive"

    set_archived = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["set_archived"] = self.set_archived
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return (
            reverse_lazy("questionnaires:question_list")
            if self.set_archived
            else reverse_lazy("questionnaires:question_list_archived")
        )

    def get_success_message(self, cleaned_data):
        return (
            _("Question archived successfully.")
            if self.set_archived
            else _("Question unarchived successfully.")
        )


class QuestionDeleteView(CustomPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    permission_required = "questionnaires.delete_question"
    model = Question
    success_url = reverse_lazy("questionnaires:question_list")
    success_message = _("Question deleted successfully.")


class SavedAnswerListView(LoginRequiredMixin, ListView):
    model = SavedAnswer
    ordering = ("question__name",)

    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset
            .select_related("question")
            .filter(user=self.request.user)
            .order_by("question__archived", "-question__use_saved_answers")
        )


class SavedAnswerUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = SavedAnswer
    form_class = SavedAnswerForm
    success_url = reverse_lazy("questionnaires:saved_answer_list")
    success_message = _("Saved answer updated successfully.")

    def get_object(self, queryset=None):
        return SavedAnswer.objects.get(
            question_id=self.kwargs["question_pk"], user=self.request.user
        )


class SavedAnswerDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = SavedAnswer
    success_url = reverse_lazy("questionnaires:saved_answer_list")
    success_message = _("Saved answer deleted successfully.")

    def get_object(self, queryset=None):
        return SavedAnswer.objects.get(
            question_id=self.kwargs["question_pk"], user=self.request.user
        )


class AggregateAnswerView(DispositionBaseViewMixin, TemplateView):
    template_name = "questionnaires/aggregate_answers.html"

    def get_question_data(self, question: Question):
        data = {
            "question": question,
        }

        all_answers = Answer.objects.filter(
            participation__shift=self.object,
            participation__state=AbstractParticipation.States.CONFIRMED,
            question=question,
        ).values_list("answer", flat=True)

        if question.type == Question.Type.TEXT:
            data["aggregation_type"] = "list"
            data["aggregated_answers"] = all_answers
        else:
            # A user's answer can be an array (multiple choice) or string (single choice)
            # We want a flat array of all individual choices made
            flat_answers = [
                answer
                for answers in all_answers
                for answer in (answers if isinstance(answers, list) else [answers])
            ]

            data["aggregation_type"] = "counts"
            data["aggregated_answers"] = dict(
                sorted(
                    Counter(flat_answers).items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            )

        return data

    def get_context_data(self, **kwargs):
        self.object: Shift

        context = super().get_context_data(**kwargs)
        context["question_data"] = [
            self.get_question_data(question)
            for question in self.object.questionnaire.questions.all()
        ]
        return context
