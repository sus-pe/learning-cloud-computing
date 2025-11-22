from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.e2e.conftest import PetStoreTester


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GET pet success not implemented",
)
async def test_get_pet_success(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)
    r = await tester.get_pet(pid, name)
    tester.assert_ok(r)
    tester.assert_json_pet(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GET pet not-found not implemented",
)
async def test_get_pet_not_found(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pet(pid, "NOPE")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Parent pet-type not-found handling not implemented",
)
async def test_get_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.get_pet("NOPE", "whatever")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="DELETE pet success flow not implemented",
)
async def test_delete_pet_success(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    pet_name = f"Pet{tester.random_type_name()}"

    # create
    r_create = await tester.post_pet(pid, json={"name": pet_name})
    tester.assert_created(r_create)
    pic_file = r_create.json()["picture"]

    # delete
    r_delete = await tester.delete_pet(pid, pet_name)
    tester.assert_no_content(r_delete)

    # picture removed
    tester.assert_pet_picture_deleted(pic_file)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="DELETE pet not-found handling not implemented",
)
async def test_delete_pet_not_found(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.delete_pet(pid, "NOPE")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="DELETE pet-type not-found not implemented",
)
async def test_delete_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.delete_pet("NOPE", "X")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT minimal pet update not implemented",
)
async def test_put_pet_success_minimal(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)
    payload = {"name": name}

    r = await tester.put_pet(pid, name, json=payload)
    tester.assert_ok(r)
    tester.assert_json_pet(r)
    tester.assert_predicate(r, lambda x: x["name"] == name)
    tester.assert_predicate(r, lambda x: x["birthdate"] == "NA")
    tester.assert_predicate(r, lambda x: x["picture"] == "NA")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT full pet update not implemented",
)
async def test_put_pet_full_update(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)

    payload = {
        "name": name,
        "birthdate": "24-10-2023",
        "picture-url": "https://example.com/new.jpg",
    }

    r = await tester.put_pet(pid, name, json=payload)
    tester.assert_ok(r)
    tester.assert_json_pet(r)
    tester.assert_predicate(r, lambda x: x["birthdate"] == "24-10-2023")
    tester.assert_predicate(r, lambda x: x["picture"].endswith(".jpg"))


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT picture dedup logic not implemented",
)
async def test_put_same_picture_url_skips_fetching(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)

    first = {"name": name, "picture-url": "https://example.com/static.jpg"}
    r1 = await tester.put_pet(pid, name, json=first)
    tester.assert_ok(r1)
    pic1 = r1.json()["picture"]

    second = {"name": name, "picture-url": "https://example.com/static.jpg"}
    r2 = await tester.put_pet(pid, name, json=second)
    tester.assert_ok(r2)
    pic2 = r2.json()["picture"]

    tester.assert_predicate(r2, lambda _: pic1 == pic2)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT missing-name validation not implemented",
)
async def test_put_pet_missing_name(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)

    r = await tester.put_pet(pid, name, json={})
    tester.assert_bad_request(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT wrong media-type detection not implemented",
)
async def test_put_pet_invalid_content_type(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)

    r = await tester.put_pet_raw(
        pid,
        name,
        raw_content=b"not-json",
        content_type="text/plain",
    )
    tester.assert_media_type_error(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT pet not-found not implemented",
)
async def test_put_pet_not_found(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.put_pet(pid, "NOPE", json={"name": "NOPE"})
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT parent pet-type not-found not implemented",
)
async def test_put_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.put_pet("NOPE", "X", json={"name": "X"})
    tester.assert_not_found(r)
