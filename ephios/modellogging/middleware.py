import uuid

from ephios.modellogging.log import log_request, log_request_id


class LoggingRequestMiddleware:
    """
    This middleware sets request as a local thread variable, making it
    available to the logging utilities to allow tracking of the
    authenticated user making a change.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        log_request.set(request)
        log_request_id.set(str(uuid.uuid4()))

        response = self.get_response(request)

        log_request.set(None)
        log_request_id.set(None)
        return response
