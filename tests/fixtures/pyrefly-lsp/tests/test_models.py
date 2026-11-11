from unittest import mock

from shop.models import load_customer


def test_load_customer() -> None:
    with mock.patch("shop.models.load_customer") as patched:
        assert load_customer("x").name == "x"
        assert patched is not None
