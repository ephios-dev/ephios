from ephios.extra.utils import dotted_get


def test_dotted_get():
    names = {"Hans": "Helmut", "Franz": "Fellmut"}
    assert dotted_get(names, "Hans") == "Helmut"
    assert dotted_get({"first_to_last": names}, "first_to_last.Hans") == "Helmut"
    assert dotted_get({"first_to_last": names}, "first_to_last.Hans") == "Helmut"
    assert dotted_get({"first_to_last": names}, "first_to_last.Lisa") is None
