import uuid

from .models import LoggedModelMixin


class LoggingRequestMiddleware:
    """Expose request to LoggedModel.
    This middleware sets request as a local thread variable, making it
    available to the model-level utilities to allow tracking of the
    authenticated user making a change.

    Taken from https://github.com/treyhunner/django-simple-history/
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        LoggedModelMixin.thread.request = request
        LoggedModelMixin.thread.request_id = str(uuid.uuid4())

        response = self.get_response(request)

        del LoggedModelMixin.thread.request
        del LoggedModelMixin.thread.request_id

        return response
