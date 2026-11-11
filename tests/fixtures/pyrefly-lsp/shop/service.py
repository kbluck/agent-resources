from shop.models import Customer, load_customer


def welcome(customer: Customer) -> str:
    return customer.greeting()


def main() -> None:
    c = load_customer("ann")
    print(welcome(c))
