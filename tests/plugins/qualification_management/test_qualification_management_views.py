import pytest
from django.urls import reverse

from ephios.core.models import Qualification, QualificationCategory, QualificationGrant


def test_qualification_reassignment(django_app, superuser, qualification_grant):
    form = django_app.get(
        reverse("qualification_management:settings_qualification_reassignment"),
        user=superuser,
        status=200,
    ).form
    other_qualification = Qualification.objects.exclude(
        id=qualification_grant.qualification_id
    ).first()
    form["current_qualifications"] = [qualification_grant.qualification_id]
    form["new_qualification"] = other_qualification.id
    form.submit().follow()
    assert QualificationGrant.objects.get(
        qualification=other_qualification, user=qualification_grant.user
    )


def test_qualification_category_view(django_app, superuser, qualification_grant):
    form = django_app.get(
        reverse("qualification_management:settings_qualification_categories"),
        user=superuser,
        status=200,
    ).form
    form["form-0-title"] = "a new name"
    assert "a new name" in form.submit().follow()


def test_create_qualification_view(django_app, superuser, qualification_grant):
    form = django_app.get(
        reverse("qualification_management:settings_qualification_create"),
        user=superuser,
        status=200,
    ).form
    form["title"] = "agile programmer"
    form["abbreviation"] = "agile"
    form["category"] = QualificationCategory.objects.get().id
    assert "agile programmer" in form.submit().follow()
    assert Qualification.objects.get(title="agile programmer").is_imported is False


def test_edit_qualification_view(django_app, superuser, qualification_grant):
    form = django_app.get(
        reverse(
            "qualification_management:settings_qualification_edit",
            kwargs=dict(pk=qualification_grant.qualification_id),
        ),
        user=superuser,
        status=200,
    ).form
    form["title"] = "Superhero"
    assert "Superhero" in form.submit().follow()


@pytest.mark.parametrize("fix_inclusions", [True, False])
def test_delete_qualification_view(django_app, superuser, qualification_grant, fix_inclusions):
    response = django_app.get(
        reverse(
            "qualification_management:settings_qualification_delete",
            kwargs=dict(pk=qualification_grant.qualification_id),
        ),
        user=superuser,
        status=200,
    )
    assert "There is 1 user with this qualification." in response
    other_qualification = Qualification.objects.exclude(
        id=qualification_grant.qualification_id
    ).first()
    response.form["move_grants_to_other_qualifications"] = [other_qualification.id]
    response.form["fix_inclusions"] = fix_inclusions
    response.form.submit()
    assert QualificationGrant.objects.get().qualification == other_qualification
