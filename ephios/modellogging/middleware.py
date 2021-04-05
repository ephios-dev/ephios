import uuid

from .log import log_request_store


class LoggingRequestMiddleware:
    """
    This middleware sets request as a local thread variable, making it
    available to the logging utilities to allow tracking of the
    authenticated user making a change.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        log_request_store.request = request
        log_request_store.request_id = str(uuid.uuid4())

        response = self.get_response(request)

        del log_request_store.request
        del log_request_store.request_id
        return response
