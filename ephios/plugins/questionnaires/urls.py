from django.urls import path

from ephios.plugins.questionnaires.views import (
    AggregateAnswerView,
    QuestionCreateView,
    QuestionDeleteView,
    QuestionListView,
    QuestionUpdateView,
    SavedAnswerDeleteView,
    SavedAnswerListView,
    SavedAnswerUpdateView,
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
    path(
        "settings/saved-answers/",
        SavedAnswerListView.as_view(),
        name="saved_answers_list",
    ),
    path(
        "settings/saved-answers/<int:question_pk>/edit/",
        SavedAnswerUpdateView.as_view(),
        name="saved_answers_edit",
    ),
    path(
        "settings/saved-answers/<int:question_pk>/delete/",
        SavedAnswerDeleteView.as_view(),
        name="saved_answers_delete",
    ),
    path(
        "shifts/<int:pk>/answers/",
        AggregateAnswerView.as_view(),
        name="shift_aggregate_answers",
    ),
]
