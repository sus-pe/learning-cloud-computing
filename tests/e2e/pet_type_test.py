from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import PetStoreTester


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Pet-type JSON contract validation not implemented",
)
async def test_pet_type_json_contract(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pet_type(pid)
    tester.assert_ok(r)
    tester.assert_json_pet_type(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Pet JSON contract validation not implemented",
)
async def test_pet_json_contract(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    petname = tester.example_pet_name(pid)
    r = await tester.get_pet(pid, petname)
    tester.assert_ok(r)
    tester.assert_json_pet(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GET /pet-types list not implemented or incorrect",
)
async def test_pet_types_list_is_array(tester: PetStoreTester) -> None:
    r = await tester.get_pet_types()
    tester.assert_ok(r)
    tester.assert_json_list(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Filtering pet-types by family not implemented",
)
async def test_pet_types_filter_by_field(tester: PetStoreTester) -> None:
    r = await tester.get_pet_types(query={"family": "Canidae"})
    tester.assert_ok(r)
    tester.assert_pet_types_family_equals(r, "Canidae")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Filtering pet-types by attribute not implemented",
)
async def test_pet_types_filter_by_attribute(tester: PetStoreTester) -> None:
    r = await tester.get_pet_types(query={"hasAttribute": "active"})
    tester.assert_ok(r)
    tester.assert_pet_types_have_attribute(r, "active")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Query parameter case-insensitivity not implemented",
)
async def test_query_is_case_insensitive(tester: PetStoreTester) -> None:
    r1 = await tester.get_pet_types(query={"family": "Canidae"})
    r2 = await tester.get_pet_types(query={"family": "canIDAE"})
    tester.assert_ok(r1)
    tester.assert_ok(r2)

    tester.assert_equal_json(r1, r2)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GET /pictures/{file} does not return correct binary data",
)
async def test_get_picture_returns_binary(tester: PetStoreTester) -> None:
    fname = tester.example_picture_name()
    r = await tester.get_picture(fname)
    tester.assert_image(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Picture not-found handling not implemented",
)
async def test_get_picture_not_available(tester: PetStoreTester) -> None:
    r = await tester.get_picture("xxxxx-nope.jpg")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="POST /pet-types creation not implemented",
)
async def test_post_pet_type_creates_new_type(tester: PetStoreTester) -> None:
    name = tester.random_type_name()
    r = await tester.post_pet_type(type_name=name)
    tester.assert_created(r)
    tester.assert_json_pet_type(r)
    tester.assert_predicate(r, lambda x: x["type"] == name)
    tester.assert_predicate(r, lambda x: x["pets"] == [])


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="POST pet-type duplicate detection not implemented",
)
async def test_post_pet_type_existing_returns_400(tester: PetStoreTester) -> None:
    existing = tester.example_pet_type_name()
    r = await tester.post_pet_type(type_name=existing)
    tester.assert_bad_request(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="POST pet-type bad payload handling not implemented",
)
async def test_post_pet_type_bad_payload_returns_400(tester: PetStoreTester) -> None:
    # missing "type" triggers bad request
    r = await tester.post_pet_type(type_name="")
    tester.assert_bad_request(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Pet-type not-found handling not implemented",
)
async def test_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.get_pet_type("NOPE-ID")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Pet not-found handling not implemented",
)
async def test_pet_not_found(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pet(pid, "NOPE")
    tester.assert_not_found(r)
