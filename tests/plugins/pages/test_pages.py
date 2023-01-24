from django.urls import reverse


def test_page_creation(django_app, superuser):
    SLUG = "testpageslug"
    response = django_app.get(reverse("pages:settings_page_list"), user=superuser)
    response = response.click(".*dd.*age.*")  # pattern for "add page"
    response.form["title"] = "page title"
    response.form["content"] = "Some **fancy markdown** content"
    response.form["slug"] = SLUG
    response.form["publicly_visible"] = True
    response.form.submit()

    response = django_app.get(reverse("pages:page_detail", kwargs=dict(slug=SLUG)))
    assert "<strong>fancy markdown</strong>" in response
