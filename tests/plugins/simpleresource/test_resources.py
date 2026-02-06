import re

from django.urls import reverse

from ephios.plugins.simpleresource.models import Resource, ResourceAllocation, ResourceCategory


def test_resource_list(django_app, superuser, resources):
    response = django_app.get(reverse("simpleresource:resource_list"), user=superuser)
    assert response.html.find(string=resources[0].title)
    assert response.html.find(string=resources[1].title)


def test_resource_edit(django_app, superuser, resources):
    form = django_app.get(
        reverse("simpleresource:resource_edit", args=[resources[0].pk]), user=superuser
    ).form
    new_title = "New Title"
    form["title"] = new_title
    response = form.submit().follow()
    assert response.status_code == 200
    assert response.html.find(string=new_title)


def test_resource_delete(django_app, superuser, resources):
    response = django_app.get(
        reverse("simpleresource:resource_delete", args=[resources[0].pk]), user=superuser
    )
    response.form.submit().follow()
    assert not Resource.objects.filter(pk=resources[0].pk).exists()


def test_resource_add(django_app, superuser, resources):
    response = django_app.get(reverse("simpleresource:resource_add"), user=superuser)
    form = response.form
    form["title"] = "New Resource"
    form["category"] = resources[0].category.pk
    form.submit().follow()
    assert Resource.objects.filter(title="New Resource").exists()


def test_resource_cannot_delete_category(django_app, superuser, resources):
    response = django_app.get(reverse("simpleresource:resource_categories"), user=superuser)
    assert (
        len(response.html.find_all("button", {"data-formset-delete-button": True})) == 0
    )  # only empty form, button in script is not found by soup


def test_resource_delete_category(django_app, superuser, resources):
    new_category = ResourceCategory.objects.create(name="New Category")
    form = django_app.get(reverse("simpleresource:resource_categories"), user=superuser).form
    form["form-1-DELETE"] = True
    form.submit()
    assert not ResourceCategory.objects.filter(pk=new_category.pk).exists()


def test_resource_allocation_display(django_app, volunteer, groups, event, resources):
    allocation = ResourceAllocation.objects.create(shift=event.shifts.first())
    allocation.resources.set([resources[0]])
    response = django_app.get(event.get_absolute_url(), user=volunteer)
    assert response.html.find(string=re.compile(f"{resources[0].title}"))
    assert not response.html.find(string=re.compile(f"{resources[1].title}"))


def test_resource_allocation_edit(django_app, superuser, groups, event, resources):
    form = django_app.get(
        reverse("core:shift_edit", kwargs={"pk": event.shifts.first().pk}), user=superuser
    ).form
    form["simple_resource-resources"].select_multiple([resources[0].pk])
    form.submit()
    assert ResourceAllocation.objects.get(shift=event.shifts.first()).resources.count() == 1
    assert (
        ResourceAllocation.objects
        .get(shift=event.shifts.first())
        .resources.filter(pk=resources[0].pk)
        .exists()
    )
