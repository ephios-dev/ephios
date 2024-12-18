from ephios.extra.templatetags.rich_text import rich_text


def test_rich_text():
    assert (
        rich_text("https://xkcd.com")
        == '<p><a href="https://xkcd.com" rel="noopener" target="_blank">https://xkcd.com</a></p>'
    )
