from django.contrib.auth.mixins import AccessMixin
from django.urls import get_resolver, reverse
from guardian.mixins import LoginRequiredMixin as GuardianLoginRequiredMixin
from guardian.mixins import PermissionRequiredMixin as GuardianPermissionRequiredMixin


def test_accounts_login(django_app):
    resp = django_app.get("/accounts/login/")
    assert resp.status_code == 200, "Should return a 200 status code"


def test_accounts_logout(django_app, superuser):
    resp = django_app.get(reverse("core:oidc_logout"), user=superuser).follow()
    assert resp.status_code == 200, "Should return a 200 status code"
    assert not hasattr(resp.request, "user")


def test_all_views_are_secured(django_app):
    # Recursively collect all URL patterns
    resolver = get_resolver()
    url_patterns = []

    def traverse(patterns):
        for pattern in patterns:
            # skip admin, auth, webpush, select2 because they are good and hard to check
            if getattr(pattern, "app_name", None) in (
                "admin",
                "django_select2",
            ):
                continue
            try:
                if pattern.urlconf_module.__name__ in (
                    "django.contrib.auth.urls",
                    "webpush.urls",
                ):
                    continue
            except AttributeError:
                pass
            if hasattr(pattern, "url_patterns"):
                traverse(pattern.url_patterns)
            elif hasattr(pattern, "pattern"):
                url_patterns.append(pattern)

    traverse(resolver.url_patterns)

    # check every pattern for its view being secured
    for pattern in url_patterns:
        view_func = pattern.callback
        if getattr(view_func, "login_required", True):
            namely = getattr(view_func, "view_class", view_func)
            assert _check_view_is_secured(view_func), (
                f"{namely} is not marked as @access_exempt, but also does not use a subclass of AccessMixin or "
                f"some other form of access control known to this test. "
                f"Please state your access intention or improve this test."
            )


def _check_view_is_secured(view_func):
    try:
        view_class = view_func.view_class
    except AttributeError:
        pass
    else:
        if issubclass(
            view_class, (AccessMixin, GuardianLoginRequiredMixin, GuardianPermissionRequiredMixin)
        ):
            # using an AccessMixin or LoginRequired/PermissionRequiredMixin from Guardian
            return True
    try:
        if hasattr(view_func.__wrapped__, "login_url"):
            # Likely using the login_required decorator
            return True
    except AttributeError:
        pass
    return False
