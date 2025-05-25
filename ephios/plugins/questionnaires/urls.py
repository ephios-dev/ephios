from django.urls import path

from ephios.plugins.questionnaires.views import (
    QuestionCreateView,
    QuestionDeleteView,
    QuestionListView,
    QuestionUpdateView,
)

app_name = "questionnaires"
urlpatterns = [
    path(
        "questions/",
        QuestionListView.as_view(),
        name="question_list",
    ),
    path(
        "questions/add/",
        QuestionCreateView.as_view(),
        name="question_add",
    ),
    path(
        "questions/<int:pk>/edit/",
        QuestionUpdateView.as_view(),
        name="question_edit",
    ),
    path(
        "questions/<int:pk>/delete/",
        QuestionDeleteView.as_view(),
        name="question_delete",
    ),
]
