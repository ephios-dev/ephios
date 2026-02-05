import pytest
from django.urls import reverse

from ephios.core.models.events import AbstractParticipation
from ephios.plugins.questionnaires.models import Answer


@pytest.fixture
def participation_with_text_answers(volunteer, shift_with_text_questions):
    shift, optional_question, required_question = shift_with_text_questions

    participation = volunteer.as_participant().new_participation(shift)
    participation.save()

    optional_answer = Answer.objects.create(
        participation=participation,
        question=optional_question,
        answer="Answer of volunteer to optional question",
    )
    required_answer = Answer.objects.create(
        participation=participation,
        question=required_question,
        answer="Answer of volunteer to required question",
    )

    return participation, optional_answer, required_answer


@pytest.fixture
def qualified_participation_with_text_answers(qualified_volunteer, shift_with_text_questions):
    shift, optional_question, required_question = shift_with_text_questions

    participation = qualified_volunteer.as_participant().new_participation(shift)
    participation.save()

    optional_answer = Answer.objects.create(
        participation=participation,
        question=optional_question,
        answer="Answer of qualified volunteer to optional question",
    )
    required_answer = Answer.objects.create(
        participation=participation,
        question=required_question,
        answer="Answer of qualified volunteer to required question",
    )

    return participation, optional_answer, required_answer


@pytest.fixture
def participation_with_choice_answer(volunteer, shift_with_required_choice_question):
    shift, question = shift_with_required_choice_question

    participation = volunteer.as_participant().new_participation(shift)
    participation.save()

    answer = Answer.objects.create(
        participation=participation,
        question=question,
        answer=["Choice #1", "Choice #2"],
    )

    return participation, answer


@pytest.fixture
def qualified_participation_with_choice_answer(
    qualified_volunteer, shift_with_required_choice_question
):
    shift, question = shift_with_required_choice_question

    participation = qualified_volunteer.as_participant().new_participation(shift)
    participation.save()

    answer = Answer.objects.create(
        participation=participation,
        question=question,
        answer=["Choice #2"],
    )

    return participation, answer


def test_show_aggregated_text_answers(
    django_app,
    superuser,
    participation_with_text_answers,
    qualified_participation_with_text_answers,
):
    participation, optional_answer, required_answer = participation_with_text_answers
    participation.state = AbstractParticipation.States.CONFIRMED
    participation.save()

    qualified_participation, qualified_optional_answer, qualified_required_answer = (
        qualified_participation_with_text_answers
    )
    qualified_participation.state = AbstractParticipation.States.CONFIRMED
    qualified_participation.save()

    response = django_app.get(
        reverse("questionnaires:shift_aggregate_answers", args=[participation.shift.pk]),
        user=superuser,
    )

    assert response.status_code == 200
    assert optional_answer.answer in response
    assert required_answer.answer in response
    assert qualified_optional_answer.answer in response
    assert qualified_required_answer.answer in response


def test_show_aggregated_choice_answers(
    django_app,
    superuser,
    participation_with_choice_answer,
    qualified_participation_with_choice_answer,
):
    participation, _ = participation_with_choice_answer
    participation.state = AbstractParticipation.States.CONFIRMED
    participation.save()

    qualified_participation, _ = qualified_participation_with_choice_answer
    qualified_participation.state = AbstractParticipation.States.CONFIRMED
    qualified_participation.save()

    response = django_app.get(
        reverse("questionnaires:shift_aggregate_answers", args=[participation.shift.pk]),
        user=superuser,
    )

    aggregated_anwers = {}
    for row in response.html.find("table").find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 0:
            continue

        aggregated_anwers[cells[0].text] = cells[1].text

    assert response.status_code == 200
    assert aggregated_anwers["Choice #1"] == "1"
    assert aggregated_anwers["Choice #2"] == "2"
    assert "Choice #3" not in aggregated_anwers


@pytest.mark.parametrize(
    "state",
    [
        AbstractParticipation.States.REQUESTED,
        AbstractParticipation.States.GETTING_DISPATCHED,
        AbstractParticipation.States.USER_DECLINED,
        AbstractParticipation.States.RESPONSIBLE_REJECTED,
    ],
)
def test_only_confirmed_in_aggregated_answers(
    django_app, superuser, participation_with_text_answers, state
):
    participation, _, _ = participation_with_text_answers
    participation.state = state
    participation.save()

    response = django_app.get(
        reverse("questionnaires:shift_aggregate_answers", args=[participation.shift.pk]),
        user=superuser,
    )

    assert response.status_code == 200
    assert "No answers so far" in response


@pytest.mark.parametrize(
    "state",
    [
        AbstractParticipation.States.REQUESTED,
        AbstractParticipation.States.CONFIRMED,
        AbstractParticipation.States.GETTING_DISPATCHED,
        AbstractParticipation.States.USER_DECLINED,
        AbstractParticipation.States.RESPONSIBLE_REJECTED,
    ],
)
def test_user_specific_answer(
    django_app,
    superuser,
    participation_with_text_answers,
    qualified_participation_with_text_answers,
    state,
):
    participation, optional_answer, required_answer = participation_with_text_answers
    participation.state = state
    participation.save()

    qualified_participation, qualified_optional_answer, qualified_required_answer = (
        qualified_participation_with_text_answers
    )
    qualified_participation.state = state
    qualified_participation.save()

    response = django_app.get(
        reverse("core:shift_disposition", args=[participation.shift.pk]), user=superuser
    )
    collapse = response.html.find(id=f"participation-collapse-{participation.pk}")
    qualified_collapse = response.html.find(
        id=f"participation-collapse-{qualified_participation.pk}"
    )

    assert response.status_code == 200
    assert collapse
    assert optional_answer.answer in collapse.text
    assert required_answer.answer in collapse.text
    assert qualified_collapse
    assert qualified_optional_answer.answer in qualified_collapse.text
    assert qualified_required_answer.answer in qualified_collapse.text
