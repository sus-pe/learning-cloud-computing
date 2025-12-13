from os import environ

from petstore.orders.__main__ import main as orders_main
from petstore.store.__main__ import main as store_main


def main() -> None:
    assert "SERVICE" in environ
    service = environ["SERVICE"]

    assert service in {"orders", "store"}
    match service:
        case "orders": orders_main()
        case "store": store_main()

if __name__ == '__main__':
    main()