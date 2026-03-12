from django.urls import reverse

from ephios.core.models.events import AbstractParticipation


def test_no_form_fields_on_plain_shift(django_app, plain_shift, volunteer):
    form = django_app.get(reverse("core:signup_action", args=[plain_shift.pk]), user=volunteer).form
    assert "questionnaires_save_answers" not in form.fields


def test_form_fields_with_questionnaire(django_app, shift_with_optional_text_question, volunteer):
    shift, question = shift_with_optional_text_question
    form = django_app.get(reverse("core:signup_action", args=[shift.pk]), user=volunteer).form

    assert "questionnaires_save_answers" in form.fields
    assert form["questionnaires_save_answers"]  # == True
    assert question.get_form_slug() in form.fields


def test_no_signup_form_if_only_optional_questions(
    django_app, shift_with_optional_text_question, volunteer
):
    shift, _ = shift_with_optional_text_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="sign_up").follow()
    shift.refresh_from_db()

    assert response.status_code == 200
    assert f"You have successfully requested a participation in {shift}." in response
    assert volunteer.as_participant() in shift.get_participants({
        AbstractParticipation.States.REQUESTED
    })


def test_signup_form_if_required_question(django_app, shift_with_required_text_question, volunteer):
    shift, question = shift_with_required_text_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="sign_up").follow()
    signup_form = response.form

    assert response.status_code == 200
    assert "We need some additional information to sign you up for this shift." in response
    assert "questionnaires_save_answers" in signup_form.fields
    assert question.get_form_slug() in signup_form.fields


def test_can_decline_with_required_question(
    django_app, shift_with_required_text_question, volunteer
):
    shift, _ = shift_with_required_text_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="decline").follow()
    shift.refresh_from_db()

    assert response.status_code == 200
    assert f"You have successfully declined {shift}." in response
    assert volunteer.as_participant() in shift.get_participants({
        AbstractParticipation.States.USER_DECLINED
    })


def test_autofill_saved_answers(
    django_app, shift_with_required_text_question, volunteer, saved_required_text_answer
):
    shift, question = shift_with_required_text_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="sign_up").follow()

    shift.refresh_from_db()
    answer = shift.participations.first().answer_set.first()

    assert response.status_code == 200
    assert f"You have successfully requested a participation in {shift}" in response
    assert volunteer.as_participant() in shift.get_participants({
        AbstractParticipation.States.REQUESTED
    })
    assert answer.question == question
    assert answer.answer == saved_required_text_answer.answer


def test_saved_answer_as_initial(
    django_app,
    shift_with_text_questions,
    volunteer,
    saved_optional_text_answer,
):
    shift, optional_question, required_question = shift_with_text_questions

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="sign_up").follow()
    signup_form = response.form

    assert response.status_code == 200
    assert "We need some additional information to sign you up for this shift." in response
    assert signup_form[optional_question.get_form_slug()].value == saved_optional_text_answer.answer
    assert required_question.get_form_slug() in signup_form.fields


def test_saved_answer_not_as_initial_when_usage_disabled(
    django_app,
    shift_with_text_questions,
    volunteer,
    saved_optional_text_answer,
):
    shift, optional_question, required_question = shift_with_text_questions
    optional_question.use_saved_answers = False
    optional_question.save()

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="sign_up").follow()
    signup_form = response.form

    assert signup_form[optional_question.get_form_slug()].value == ""


def test_show_choices(django_app, volunteer, shift_with_required_choice_question):
    shift, question = shift_with_required_choice_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    response = form.submit(name="signup_choice", value="sign_up").follow()

    assert response.status_code == 200
    for choice in question.choices:
        assert response.html.find("input", attrs={"type": "radio", "value": choice})
