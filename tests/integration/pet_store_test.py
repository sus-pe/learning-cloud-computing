from typing import TYPE_CHECKING

import pytest

from petstore import PetEntity, PetStoreResource, PetTypeEntity

if TYPE_CHECKING:
    from petstore.tester import PetStoreTester


async def test_post_pet_type_creates_new_type(tester: PetStoreTester) -> None:
    p = await tester.assert_first_example_pet_type_post_created()
    # Same pet, second time should fail.
    await tester.assert_repeating_post_pet_type_name_error(type_name=p.type)


async def test_post_pet_type_nonexisting(tester: PetStoreTester) -> None:
    r = await tester.unsafe_post_pet_type("this is not a real pet type")
    tester.assert_bad_request(r)


async def test_post_pet_type_unsupported_type(tester: PetStoreTester) -> None:
    r = await tester.unsafe_post_pet_type(123)
    tester.assert_media_type_error(r)


async def test_get_pet_type(tester: PetStoreTester) -> None:
    assert len(await tester.get_pet_types()) == 0

    await tester.assert_first_example_pet_type_post_created()
    r = await tester.get_pet_types()
    assert len(r) == 1
    assert r[0] == tester.example_empty_pet_type

    assert len(await tester.get_pet_types(attr="zero-matches-attr")) == 0

    assert r == await tester.get_pet_types(family="Canidae")
    assert len(await tester.get_pet_types(non_sensical_query=True)) == 0


async def test_delete_pet_types_method_not_allowed(tester: PetStoreTester) -> None:
    r = await tester.unsafe_put(PetStoreResource.PET_TYPE)
    tester.assert_method_not_allowed(r)


async def test_put_pet_types_method_not_allowed(tester: PetStoreTester) -> None:
    r = await tester.unsafe_delete(PetStoreResource.PET_TYPE)
    tester.assert_method_not_allowed(r)


async def test_get_specific_pet_type(tester: PetStoreTester) -> None:
    not_found_get_respone = await tester.unsafe_get_pet_type(
        tester.example_empty_pet_type.type
    )
    tester.assert_not_found(not_found_get_respone)

    expected = await tester.assert_first_example_pet_type_post_created()
    get_response = await tester.unsafe_get_pet_type(expected.id)
    tester.assert_ok(get_response)
    body = tester.assert_json(get_response, dict)
    actual = PetTypeEntity.model_validate(body)
    assert expected == actual

    delete_response = await tester.unsafe_delete_pet_type(expected.id)
    tester.assert_no_content(delete_response)

    not_found_delete_response = await tester.unsafe_delete_pet_type(expected.id)
    tester.assert_not_found(not_found_delete_response)


@pytest.mark.xfail(raises=NotImplementedError)
async def test_delete_populated_pet_type(tester: PetStoreTester) -> None:
    # Should return 400
    raise NotImplementedError


async def test_put_pet_type_id_method_not_allowed(tester: PetStoreTester) -> None:
    r = await tester.unsafe_put(PetStoreResource.PET_TYPE_ID)
    tester.assert_method_not_allowed(r)


async def test_post_pet_type_id_method_not_allowed(tester: PetStoreTester) -> None:
    r = await tester.unsafe_post(PetStoreResource.PET_TYPE_ID)
    tester.assert_method_not_allowed(r)


async def test_post_new_pet_to_type(tester: PetStoreTester) -> None:
    pt = tester.example_empty_pet_type
    p = tester.example_pet
    picture_url = "https://api-ninjas.com/images/dogs/golden_retriever.jpg"
    r = await tester.unsafe_post_pet(
        type_id=pt.id,
        name=p.name,
        birthdate=p.birthdate,
        picture_url=picture_url,
    )
    tester.assert_not_found(r)
    r = await tester.unsafe_get_pets(
        type_id=pt.id,
    )
    tester.assert_not_found(r)

    created_type = await tester.assert_first_example_pet_type_post_created()
    assert len(await tester.get_pets(type_id=pt.id)) == 0

    for malformed_date in (
        "incorrect",
        "21.01.1998",
        "232-23/2025",
        "30-01-25",
        "12-30-2025",
    ):
        r = await tester.unsafe_post_pet(
            type_id=created_type.id,
            name=p.name,
            birthdate=malformed_date,
            picture_url=picture_url,
        )
        tester.assert_malformed(r)

    r = await tester.unsafe_post_pet(
        type_id=created_type.id,
        name=p.name,
        birthdate=p.birthdate,
        picture_url=picture_url,
    )
    tester.assert_created(r)
    body = tester.assert_json(r, dict)
    p = PetEntity.model_validate(body)
    assert p == tester.example_pet

    pets = await tester.get_pets(type_id=pt.id)
    assert len(pets) == 1
    assert pets[0] == p
