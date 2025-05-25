from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.questionnaires.forms import QuestionForm
from ephios.plugins.questionnaires.models import Question


class QuestionListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "questionnaires.view_question"
    model = Question
    ordering = ("name", "question_text")


class QuestionCreateView(CustomPermissionRequiredMixin, CreateView):
    permission_required = "questionnaires.add_question"
    accept_object_perms = False
    form_class = QuestionForm
    template_name = "questionnaires/question_form.html"
    success_url = reverse_lazy("questionnaires:question_list")


class QuestionUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "questionnaires.change_question"
    form_class = QuestionForm
    template_name = "questionnaires/question_form.html"
    success_url = reverse_lazy("questionnaires:question_list")

    def get_queryset(self):
        return Question.objects.filter(pk=self.kwargs["pk"])


class QuestionDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "questionnaires.delete_question"
    model = Question
    success_url = reverse_lazy("questionnaires:question_list")
