from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import PetStoreTester


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GET /pet-types/{id} not implemented yet",
)
async def test_get_pet_type_success(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.get_pet_type(pid)
    tester.assert_ok(r)
    tester.assert_json_pet_type(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Not-found handling for GET /pet-types/{id} not implemented",
)
async def test_get_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.get_pet_type("NOPE-ID")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="PUT not allowed for pet-types not implemented",
)
async def test_put_not_allowed(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.put_pet_type(pid, json={"x": "y"})
    tester.assert_method_not_allowed(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="DELETE empty pet-type success not implemented",
)
async def test_delete_pet_type_success_when_no_pets(tester: PetStoreTester) -> None:
    name = tester.random_type_name()

    r_create = await tester.post_pet_type(type_name=name)
    tester.assert_created(r_create)
    new_id = tester.require_key(r_create.json(), "id", str)

    r_delete = await tester.delete_pet_type(new_id)
    tester.assert_no_content(r_delete)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="DELETE pet-type with existing pets not implemented",
)
async def test_delete_pet_type_with_pets_fails(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()

    r_type = await tester.get_pet_type(pid)
    tester.assert_ok(r_type)
    tester.assert_pet_type_has_pets(r_type)

    r_delete = await tester.delete_pet_type(pid)
    tester.assert_bad_request(r_delete)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="DELETE pet-type not-found not implemented",
)
async def test_delete_pet_type_not_found(tester: PetStoreTester) -> None:
    r = await tester.delete_pet_type("XXXX-NOT-THERE")
    tester.assert_not_found(r)
