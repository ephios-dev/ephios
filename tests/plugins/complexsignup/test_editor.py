import json

from django.urls import reverse

from ephios.plugins.complexsignup.models import BuildingBlock

NEW_ATOMIC_BLOCK_DATA = {
    "id": None,
    "uuid": "969dd854-dd82-4714-940f-8a0d219c056a",
    "name": "Test",
    "block_type": "atomic",
    "sub_compositions": [],
    "allow_more": False,
    "qualification_requirements": [],
    "positions": [],
}


def test_submitting_no_blocks_does_not_delete(django_app, superuser):
    response = django_app.get(reverse("complexsignup:blocks_editor"), user=superuser, status=200)
    response.form["blocks"] = json.dumps([
        NEW_ATOMIC_BLOCK_DATA,
    ])
    response = response.form.submit().follow()
    assert BuildingBlock.objects.count() == 1
    response.form["blocks"] = json.dumps([])
    response = response.form.submit().follow()
    assert BuildingBlock.objects.count() == 1
    response.form["blocks"] = json.dumps([{"deleted": True, **NEW_ATOMIC_BLOCK_DATA}])
    response = response.form.submit().follow()
    assert BuildingBlock.objects.count() == 0


def test_name_cannot_be_empty_unless_deleted(django_app, superuser):
    response = django_app.get(reverse("complexsignup:blocks_editor"), user=superuser, status=200)
    response.form["blocks"] = json.dumps([
        NEW_ATOMIC_BLOCK_DATA,
    ])
    response = response.form.submit().follow()
    assert BuildingBlock.objects.count() == 1
    response.form["blocks"] = json.dumps([
        {
            **NEW_ATOMIC_BLOCK_DATA,
            "name": "",
        },
    ])
    response = response.form.submit()
    assert response.context["form"].errors
    assert BuildingBlock.objects.count() == 1
    response.form["blocks"] = json.dumps([
        {
            **NEW_ATOMIC_BLOCK_DATA,
            "name": "",
            "deleted": True,
        },
    ])
    response = response.form.submit().follow()
    assert BuildingBlock.objects.count() == 0


def test_delete_unsaved_block_with_empty_name_and_invalid_form(django_app, superuser):
    response = django_app.get(reverse("complexsignup:blocks_editor"), user=superuser, status=200)
    response.form["blocks"] = json.dumps([
        {
            **NEW_ATOMIC_BLOCK_DATA,
            "name": "",
            "deleted": True,
        },
    ])
    response = response.form.submit().follow()
    assert BuildingBlock.objects.count() == 0


def test_no_cycle_in_composite_blocks(django_app, superuser):
    response = django_app.get(reverse("complexsignup:blocks_editor"), user=superuser, status=200)
    response.form["blocks"] = json.dumps([
        {
            "id": None,
            "uuid": "dd508995-8bbf-45ef-9432-b3e6216c574a",
            "name": "A",
            "block_type": "composite",
            "sub_compositions": [
                {
                    "id": None,
                    "sub_block": "7c1c45b7-4707-4f9a-a9b8-f204c0e259b2",
                    "optional": False,
                },
            ],
            "allow_more": False,
            "qualification_requirements": [],
            "positions": [],
        },
        {
            "id": None,
            "uuid": "7c1c45b7-4707-4f9a-a9b8-f204c0e259b2",
            "name": "B",
            "block_type": "composite",
            "sub_compositions": [
                {
                    "id": None,
                    "sub_block": "dd508995-8bbf-45ef-9432-b3e6216c574a",
                    "optional": False,
                },
            ],
            "allow_more": False,
            "qualification_requirements": [],
            "positions": [],
        },
    ])
    response = response.form.submit()
    assert BuildingBlock.objects.count() == 0
    assert response.context["form"].errors
