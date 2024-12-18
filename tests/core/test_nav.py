import re

from django.urls import reverse


def bs_find_all_substring(element, substring):
    return element.find_all(string=re.compile(rf".*{substring}.*"))


def test_navbar_content(django_app, groups, planner, volunteer, manager):
    navbar = django_app.get(reverse("core:home"), user=volunteer).html.select(".navbar")[0]
    assert bs_find_all_substring(navbar, "Events")
    assert not bs_find_all_substring(navbar, "Groups")
    assert not bs_find_all_substring(navbar, "Users")

    navbar = django_app.get(reverse("core:home"), user=planner).html.select(".navbar")[0]
    assert bs_find_all_substring(navbar, "Events")
    assert not bs_find_all_substring(navbar, "Groups")
    assert not bs_find_all_substring(navbar, "Users")

    navbar = django_app.get(reverse("core:home"), user=manager).html.select(".navbar")[0]
    assert bs_find_all_substring(navbar, "Events")
    assert bs_find_all_substring(navbar, "Groups")
    assert bs_find_all_substring(navbar, "Users")
