from django.urls import reverse

from ephios.plugins.simpleresource.models import Resource, ResourceCategory


def test_resource_list(django_app, superuser, resources):
    response = django_app.get(reverse("simpleresource:resource_list"), user=superuser)
    assert response.html.find(text=resources[0].title)
    assert response.html.find(text=resources[1].title)


def test_resource_edit(django_app, superuser, resources):
    form = django_app.get(
        reverse("simpleresource:resource_edit", args=[resources[0].pk]), user=superuser
    ).form
    new_title = "New Title"
    form["title"] = new_title
    response = form.submit().follow()
    assert response.status_code == 200
    assert response.html.find(text=new_title)


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
        len(response.html.findAll("button", {"data-formset-delete-button": ""})) == 1
    )  # only empty form


def test_resource_delete_category(django_app, superuser, resources):
    new_category = ResourceCategory.objects.create(name="New Category")
    form = django_app.get(reverse("simpleresource:resource_categories"), user=superuser).form
    form["form-1-DELETE"] = True
    form.submit()
    assert not ResourceCategory.objects.filter(pk=new_category.pk).exists()
