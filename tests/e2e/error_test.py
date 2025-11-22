from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import PetStoreTester


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Malformed JSON handling not implemented yet",
)
async def test_malformed_data_error(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.post_pet(
        pid,
        raw_content=b"not-json",
        content_type="application/json",
    )
    tester.assert_malformed(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Not-found handling not implemented yet",
)
async def test_not_found_error(tester: PetStoreTester) -> None:
    r = await tester.get_pet_type("NOPE")
    tester.assert_not_found(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Media-type validation not implemented yet",
)
async def test_wrong_media_type_error(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    r = await tester.post_pet(
        pid,
        raw_content=b"{}",
        content_type="text/plain",
    )
    tester.assert_media_type_error(r)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Server-side picture download wrapper not implemented yet",
)
async def test_server_error_wrapper(tester: PetStoreTester) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)
    r = await tester.put_pet_picture(
        pid,
        name,
        "https://bad.invalid/file.jpg",
    )
    tester.assert_server_error(r)
