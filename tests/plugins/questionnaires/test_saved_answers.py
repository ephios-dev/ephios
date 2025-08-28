from django.urls import reverse

from ephios.plugins.questionnaires.models import SavedAnswer


def test_saved_answer_list(
    django_app, volunteer, saved_optional_text_answer, saved_required_text_answer
):
    response = django_app.get(reverse("questionnaires:saved_answer_list"), user=volunteer)
    assert saved_optional_text_answer.question.name in response
    assert saved_optional_text_answer.question.question_text in response
    assert saved_optional_text_answer.answer in response
    assert saved_required_text_answer.question.name in response
    assert saved_required_text_answer.question.question_text in response
    assert saved_required_text_answer.answer in response


def test_saved_answer_edit(django_app, volunteer, saved_optional_text_answer):
    form = django_app.get(
        reverse("questionnaires:saved_answer_edit", args=[saved_optional_text_answer.question.pk]),
        user=volunteer,
    ).form

    answer = "Edited saved answer"
    form["answer"] = answer

    response = form.submit().follow()
    saved_optional_text_answer.refresh_from_db()

    assert response.status_code == 200
    assert answer in response
    assert saved_optional_text_answer.answer == answer


def test_saved_answer_edit_empty(django_app, volunteer, saved_optional_text_answer):
    form = django_app.get(
        reverse("questionnaires:saved_answer_edit", args=[saved_optional_text_answer.question.pk]),
        user=volunteer,
    ).form
    form["answer"] = ""
    response = form.submit()

    assert "This field is required." in response


def test_saved_answer_delete(django_app, volunteer, saved_optional_text_answer):
    form = django_app.get(
        reverse(
            "questionnaires:saved_answer_delete", args=[saved_optional_text_answer.question.pk]
        ),
        user=volunteer,
    ).form

    response = form.submit().follow()

    assert response.status_code == 200
    assert not SavedAnswer.objects.filter(pk=saved_optional_text_answer.pk).exists()


def test_save_answer(django_app, volunteer, shift_with_required_text_question):
    shift, question = shift_with_required_text_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    signup_form = form.submit(name="signup_choice", value="sign_up").follow().form

    answer = "Answer to required text question"
    signup_form[question.get_form_slug()] = answer
    signup_form["questionnaires_save_answers"] = True

    response = signup_form.submit(name="signup_choice", value="sign_up").follow()
    saved_answer = volunteer.savedanswer_set.filter(question=question).first()

    assert response.status_code == 200
    assert saved_answer is not None
    assert saved_answer.answer == answer


def test_dont_save_answer(django_app, volunteer, shift_with_required_text_question):
    shift, question = shift_with_required_text_question

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    signup_form = form.submit(name="signup_choice", value="sign_up").follow().form

    answer = "Answer to required text question"
    signup_form[question.get_form_slug()] = answer
    signup_form["questionnaires_save_answers"] = False

    response = signup_form.submit(name="signup_choice", value="sign_up").follow()

    assert response.status_code == 200
    assert not volunteer.savedanswer_set.filter(question=question).exists()


def test_dont_save_answer_when_usage_disabled(
    django_app, volunteer, shift_with_required_text_question
):
    shift, question = shift_with_required_text_question
    question.use_saved_answers = False
    question.save()

    form = django_app.get(shift.event.get_absolute_url(), user=volunteer).form
    signup_form = form.submit(name="signup_choice", value="sign_up").follow().form

    answer = "Answer to required text question"
    signup_form[question.get_form_slug()] = answer
    assert "questionnaires_save_answers" not in signup_form.fields

    signup_form.submit(name="signup_choice", value="sign_up")
    assert not volunteer.savedanswer_set.filter(question=question).exists()
