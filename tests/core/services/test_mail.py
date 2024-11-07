import re

from ephios.core.templatetags.email_extras import base64_static_file

RE_EPHIOS_LOGO_BASE64 = (
    r"^iVBORw0KGgoAAAANSUhEUgAAAdAAAACuCAYAAACGAlwFAAAACX.*"
    r"AOhLlmX/D1gLbnt68D6OAAAAAElFTkSuQmCC$"
)


def test_base64_static_file_encode():
    encoded = base64_static_file("ephios/img/ephios-text-black.png")
    assert re.compile(RE_EPHIOS_LOGO_BASE64).match(encoded)
