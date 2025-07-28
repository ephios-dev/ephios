from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from guardian.mixins import LoginRequiredMixin

from ephios.core.models.events import Shift
from ephios.core.signup.disposition import DispositionBaseViewMixin
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.questionnaires.forms import QuestionForm, SavedAnswerForm
from ephios.plugins.questionnaires.models import Question, SavedAnswer


class QuestionListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "questionnaires.view_question"
    model = Question
    ordering = ("name", "question_text")


class QuestionCreateView(CustomPermissionRequiredMixin, CreateView):
    permission_required = "questionnaires.add_question"
    accept_object_perms = False
    model = Question
    form_class = QuestionForm
    template_name = "questionnaires/question_form.html"
    success_url = reverse_lazy("questionnaires:question_list")


class QuestionUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "questionnaires.change_question"
    model = Question
    form_class = QuestionForm
    success_url = reverse_lazy("questionnaires:question_list")


class QuestionDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "questionnaires.delete_question"
    model = Question
    success_url = reverse_lazy("questionnaires:question_list")


class SavedAnswerListView(LoginRequiredMixin, ListView):
    model = SavedAnswer

    def get_queryset(self):
        return SavedAnswer.objects.filter(user=self.request.user).order_by("question__name")


class SavedAnswerUpdateView(LoginRequiredMixin, UpdateView):
    model = SavedAnswer
    form_class = SavedAnswerForm
    success_url = reverse_lazy("questionnaires:saved_answers_list")

    def get_object(self, queryset=None):
        return SavedAnswer.objects.get(
            question_id=self.kwargs["question_pk"], user=self.request.user
        )


class SavedAnswerDeleteView(LoginRequiredMixin, DeleteView):
    model = SavedAnswer
    success_url = reverse_lazy("questionnaires:saved_answers_list")

    def get_object(self, queryset=None):
        return SavedAnswer.objects.get(
            question_id=self.kwargs["question_pk"], user=self.request.user
        )


class AggregateAnswerView(DispositionBaseViewMixin, TemplateView):
    template_name = "questionnaires/aggregate_answers.html"

    def get_context_data(self, **kwargs):
        self.object: Shift
        print(self.object, self.object.questionnaire)

        context = super().get_context_data(**kwargs)

        return context
