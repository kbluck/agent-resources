from dataclasses import dataclass


@dataclass
class Customer:
    """A registered customer."""

    name: str
    email: str

    def greeting(self) -> str:
        return f"Hello, {self.name}"


class VipCustomer(Customer):
    def greeting(self) -> str:
        return f"Welcome back, {self.name}"


def load_customer(name):
    return Customer(name, name + "@example.com")


def find_customer(name: str) -> "Customer | None":
    return load_customer(name) if name else None
