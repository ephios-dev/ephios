from csp.constants import UNSAFE_EVAL
from csp.decorators import csp_update
from django.utils.decorators import method_decorator


def csp_allow_unsafe_eval(view_class):
    """
    We use a CSP, but also use on-the-fly-compiled vue components. Vue uses `eval` in its compiler
    to build the templates. Without a build-step for our vue components, we can't get rid of it.
    Use this decorator on view classes to ease the csp to allow that unsafe eval.
    """
    return method_decorator(
        csp_update(
            {"script-src": [UNSAFE_EVAL]},
        ),
        name="dispatch",
    )(view_class)
