def test_healthcheck(django_app):
    django_app.get("/healthcheck/", status=200)
