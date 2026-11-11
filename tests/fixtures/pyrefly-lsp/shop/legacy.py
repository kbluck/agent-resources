from shop import models


def legacy_name() -> str:
    return models.load_customer("legacy").name
