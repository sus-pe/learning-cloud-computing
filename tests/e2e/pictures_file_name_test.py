from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.e2e.conftest import PetStoreTester


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GET picture success not implemented",
)
async def test_picture_success(tester: PetStoreTester) -> None:
    fname = tester.example_picture_name()
    r = await tester.get_picture(fname)
    tester.assert_image(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Picture not-found handling not implemented",
)
async def test_picture_not_found(tester: PetStoreTester) -> None:
    r = await tester.get_picture("not-here.jpg")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Picture allowed-methods enforcement not implemented",
)
async def test_picture_allowed_methods(tester: PetStoreTester) -> None:
    fname = tester.example_picture_name()
    await tester.assert_only_get_allowed(tester.client, f"/pictures/{fname}")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Picture stability (consistent bytes) not implemented",
)
async def test_picture_stability(tester: PetStoreTester) -> None:
    fname = tester.example_picture_name()
    r1 = await tester.get_picture(fname)
    tester.assert_image(r1)
    r2 = await tester.get_picture(fname)
    tester.assert_image(r2)
    tester.assert_same_picture_bytes(r1, r2)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Picture deletion after pet removal not implemented",
)
async def test_picture_deleted_after_pet_removed(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = f"Temp{tester.random_type_name()}"

    # create pet
    r_create = await tester.post_pet(pid, json={"name": name})
    tester.assert_created(r_create)
    picture = r_create.json()["picture"]

    # picture should exist before delete
    tester.assert_picture_exists(picture)

    # delete pet
    r_del = await tester.delete_pet(pid, name)
    tester.assert_no_content(r_del)

    # picture should be gone
    tester.assert_picture_deleted(picture)
