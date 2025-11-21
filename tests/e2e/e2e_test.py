from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient, Response

    from tests.conftest import PetStoreTester


async def test_pet_types_collection_reachable(
    client: AsyncClient,
    tester: PetStoreTester,
) -> None:
    r: Response = await client.get("/pet-types")
    assert tester.validate_status(r.status_code)


async def test_pet_types_item_reachable(
    client: AsyncClient,
    tester: PetStoreTester,
) -> None:
    r: Response = await client.get("/pet-types/123")
    assert tester.validate_status(r.status_code)


async def test_pet_types_pets_collection_reachable(
    client: AsyncClient,
    tester: PetStoreTester,
) -> None:
    r: Response = await client.get("/pet-types/123/pets")
    assert tester.validate_status(r.status_code)


async def test_pet_types_pets_item_reachable(
    client: AsyncClient,
    tester: PetStoreTester,
) -> None:
    r: Response = await client.get("/pet-types/123/pets/fluffy")
    assert tester.validate_status(r.status_code)


async def test_pictures_item_reachable(
    client: AsyncClient,
    tester: PetStoreTester,
) -> None:
    r: Response = await client.get("/pictures/sample.jpg")
    assert tester.validate_status(r.status_code)
