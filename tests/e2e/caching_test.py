from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.e2e.conftest import PetStoreTester


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Picture should not be re-downloaded when URL is unchanged",
)
async def test_picture_not_redownloaded_when_url_unchanged(
    tester: PetStoreTester,
) -> None:
    pid = tester.example_pet_type_id()
    name = tester.example_pet_name(pid)
    url = "https://example.com/static.jpg"

    r1 = await tester.put_pet_picture(pid, name, url)
    tester.assert_ok(r1)
    body1 = tester.assert_json(r1)
    pic = tester.require_key(body1, "picture", str)

    before_mtime = tester.get_picture_mtime(pic)

    r2 = await tester.put_pet_picture(pid, name, url)
    tester.assert_ok(r2)
    body2 = tester.assert_json(r2)
    tester.require_key(body2, "picture", str)

    assert before_mtime == tester.get_picture_mtime(pic)
