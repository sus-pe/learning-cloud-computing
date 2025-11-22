from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import PetStoreTester


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_get_pets_success(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pets(pid)
    tester.assert_ok(r)
    tester.assert_json_list(r)


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_get_pets_not_found(tester: PetStoreTester) -> None:
    r = await tester.get_pets("NOPE-ID")
    tester.assert_not_found(r)


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_post_pet_minimal_success(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = f"Pet{tester.random_type_name()}"
    r = await tester.post_pet_minimal(pid, name)

    tester.assert_created(r)
    tester.assert_json_pet(r)
    tester.assert_pet_field_equals(r, "name", name)
    tester.assert_pet_defaults(r)


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_post_pet_full_payload_success(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = f"Pet{tester.random_type_name()}"
    payload = {
        "name": name,
        "birthdate": "24-10-2023",
        "picture-url": "https://example.com/test.jpg",
    }
    r = await tester.post_pet(pid, json=payload)

    tester.assert_created(r)
    tester.assert_json_pet(r)
    tester.assert_pet_field_equals(r, "name", name)
    tester.assert_pet_field_equals(r, "birthdate", "24-10-2023")
    tester.assert_pet_picture_endswith(r, ".jpg")


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_post_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.post_pet("NOPE", json={"name": "X"})
    tester.assert_not_found(r)


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_post_pet_missing_name(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.post_pet(pid, json={"birthdate": "24-10-2023"})
    tester.assert_status(r, tester.codes.BAD_REQUEST)


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_post_pet_invalid_content_type(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.post_pet_raw(
        pid,
        raw_content=b"not-json",
        content_type="text/plain",
    )
    tester.assert_media_type_error(r)


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_get_pets_birthdate_gt(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pets(pid, query={"birthdateGT": "01-01-2020"})
    tester.assert_ok(r)
    pets = tester.assert_json_list(r)
    tester.assert_birthdate_gt(pets, "01-01-2020")


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_get_pets_birthdate_lt(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pets(pid, query={"birthdateLT": "01-01-2020"})
    tester.assert_ok(r)
    pets = tester.assert_json_list(r)
    tester.assert_birthdate_lt(pets, "01-01-2020")


@pytest.mark.xfail(strict=True, raises=AssertionError)
async def test_get_pets_birthdate_between(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pets(
        pid,
        query={"birthdateGT": "01-01-2010", "birthdateLT": "01-01-2030"},
    )
    tester.assert_ok(r)
    pets = tester.assert_json_list(r)
    tester.assert_birthdate_between(pets, "01-01-2010", "01-01-2030")
