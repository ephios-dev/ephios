from django.urls import reverse

from ephios.plugins.questionnaires.models import Question


def test_question_list(django_app, superuser, optional_text_question, required_text_question):
    response = django_app.get(reverse("questionnaires:question_list"), user=superuser)
    assert optional_text_question.name in response
    assert optional_text_question.question_text in response
    assert required_text_question.name in response
    assert required_text_question.question_text in response


def test_question_edit(django_app, superuser, optional_text_question):
    form = django_app.get(
        reverse("questionnaires:question_edit", args=[optional_text_question.pk]), user=superuser
    ).form

    new_data = {
        "name": "New Name",
        "question_text": "New Question Text",
        "description": "New Description",
        "required": True,
    }

    for key, value in new_data.items():
        form[key] = value

    response = form.submit().follow()
    optional_text_question.refresh_from_db()

    assert response.status_code == 200
    assert new_data["name"] in response

    for key, value in new_data.items():
        assert getattr(optional_text_question, key) == value


def test_question_delete(django_app, superuser, optional_text_question):
    form = django_app.get(
        reverse("questionnaires:question_delete", args=[optional_text_question.pk]), user=superuser
    ).form

    response = form.submit().follow()

    assert response.status_code == 200
    assert not Question.objects.filter(pk=optional_text_question.pk).exists()


def test_question_add(django_app, superuser):
    form = django_app.get(reverse("questionnaires:question_create"), user=superuser).form

    data = {
        "name": "New Question",
        "question_text": "Question Text",
        "description": "Question Description",
        "type": Question.Type.TEXT,
        "required": True,
    }

    for key, value in data.items():
        form[key] = value

    response = form.submit().follow()
    question = Question.objects.filter(name=data["name"]).first()

    assert response.status_code == 200
    assert question is not None

    for key, value in data.items():
        assert getattr(question, key) == value


def test_archive_question(django_app, superuser, optional_text_question):
    form = django_app.get(
        reverse("questionnaires:question_archive", args=[optional_text_question.pk]), user=superuser
    ).form
    response = form.submit().follow()

    archived_list = django_app.get(reverse("questionnaires:question_list_archived"), user=superuser)

    assert response.status_code == 200
    assert optional_text_question.name not in response
    assert optional_text_question.name in archived_list


def test_unarchive_question(django_app, superuser, optional_text_question):
    optional_text_question.archived = True
    optional_text_question.save()

    form = django_app.get(
        reverse("questionnaires:question_unarchive", args=[optional_text_question.pk]),
        user=superuser,
    ).form
    response = form.submit().follow()

    unarchived_list = django_app.get(reverse("questionnaires:question_list"), user=superuser)

    assert response.status_code == 200
    assert optional_text_question.name not in response
    assert optional_text_question.name in unarchived_list


def test_cannot_delete_used_question(django_app, superuser, shift_with_optional_text_question):
    response = django_app.get(reverse("questionnaires:question_list"), user=superuser)

    assert response.html.find("a", class_="disabled").find("span", string="Delete")
