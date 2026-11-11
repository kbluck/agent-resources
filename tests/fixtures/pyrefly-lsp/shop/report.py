import shop.models
from . import models
from .models import load_customer as lc

__all__ = ["summary"]


class Report:
    def greeting(self) -> str:
        return "Quarterly report"


def summary() -> str:
    a = shop.models.load_customer("a")
    b = models.load_customer("b")
    c = lc("c")
    return " ".join([a.greeting(), b.greeting(), c.greeting(), Report().greeting()])
