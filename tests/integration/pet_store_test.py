import mimetypes
from typing import TYPE_CHECKING

from petstore.store.api import PetStoreResource
from petstore.store.model import PetEntity, PetTypeEntity

if TYPE_CHECKING:
    from petstore import PetStoreTester


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


async def test_delete_populated_pet_type(tester: PetStoreTester) -> None:
    pet_type = await tester.assert_first_example_pet_type_post_created()
    await tester.post_dummy_pet(pet_type.id)
    r = await tester.unsafe_delete_pet_type(pet_type.id)
    tester.assert_malformed(r)


async def test_put_pet_type_id_method_not_allowed(tester: PetStoreTester) -> None:
    r = await tester.unsafe_put(PetStoreResource.PET_TYPE_ID)
    tester.assert_method_not_allowed(r)


async def test_post_pet_type_id_method_not_allowed(tester: PetStoreTester) -> None:
    r = await tester.unsafe_post(PetStoreResource.PET_TYPE_ID)
    tester.assert_method_not_allowed(r)


async def test_post_new_pet_to_type(tester: PetStoreTester) -> None:
    pt = tester.example_empty_pet_type
    p = tester.example_pet
    r = await tester.unsafe_post_pet(
        type_id=pt.id,
        name=p.name,
        birthdate=p.birthdate,
        picture_url=tester.example_picture_url,
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
            picture_url=tester.example_picture_url,
        )
        tester.assert_malformed(r)

    p = await tester.post_new_pet(
        pet_name=p.name,
        pet_type=created_type.id,
        birthdate=p.birthdate,
        picture_url=tester.example_picture_url,
    )
    assert p == tester.example_pet

    pets = await tester.get_pets(
        type_id=pt.id,
        birthdate_lt="25-10-2023",
        birthdate_gt="23-10-2023",
    )
    assert len(pets) == 1
    assert pets[0] == p

    r = await tester.unsafe_get_pets(
        type_id=pt.id,
        birthdate_lt="25-30-2023",
        birthdate_gt="23-10-2023",
    )
    tester.assert_malformed(r)


async def test_get_specific_pet(tester: PetStoreTester) -> None:
    pt = tester.example_empty_pet_type
    p = tester.example_pet
    r = await tester.unsafe_get_pet(type_id=pt.id, pet_name=p.name)
    tester.assert_not_found(r)

    created_type = await tester.assert_first_example_pet_type_post_created()
    pet = await tester.post_new_pet(pet_type=created_type.id, pet_name=p.name)

    actual_pet = await tester.get_pet(type_id=created_type.id, pet_name=p.name)
    assert pet == actual_pet


async def test_delete_specific_pet(tester: PetStoreTester) -> None:
    pt = tester.example_empty_pet_type
    p = tester.example_pet
    r = await tester.unsafe_delete_pet(type_id=pt.id, pet_name=p.name)
    tester.assert_not_found(r)

    created_type = await tester.assert_first_example_pet_type_post_created()
    pet = await tester.post_new_pet(
        pet_type=created_type.id,
        pet_name=p.name,
        picture_url=tester.example_picture_url,
    )
    sanity_check_on_pet_type = await tester.get_pet_type(created_type.id)
    assert pet.name in sanity_check_on_pet_type.pets

    r = await tester.unsafe_get_picture(pet.picture)
    tester.assert_ok(r)
    content_type = r.headers["content-type"]
    assert mimetypes.guess_extension(content_type) == ".jpg"
    tester.assert_equal_images(r.content, tester.example_picture_bytes)

    r = await tester.unsafe_delete_pet(type_id=created_type.id, pet_name=p.name)
    tester.assert_no_content(r)

    r = await tester.unsafe_get_picture(pet.picture)
    tester.assert_not_found(r)

    modified_type = await tester.get_pet_type(created_type.id)
    assert pet.name not in modified_type.pets


async def test_put_specific_pet(tester: PetStoreTester) -> None:
    pt = tester.example_empty_pet_type
    p = tester.example_pet
    r = await tester.unsafe_put_pet(type_id=pt.id, pet_name=p.name)
    tester.assert_not_found(r)

    created_type = await tester.assert_first_example_pet_type_post_created()
    old_pet = await tester.post_new_pet(
        pet_type=created_type.id,
        pet_name=p.name,
        picture_url=tester.example_picture_url,
    )

    expected_new_pet = PetEntity(
        name="jamie", birthdate="05-01-1997", picture="1.jamie.jpg"
    )
    example_picture_url2 = tester.example_picture_url2
    r = await tester.unsafe_put_pet(
        type_id=created_type.id,
        pet_name=old_pet.name,
        birthdate=expected_new_pet.birthdate,
        picture_url=example_picture_url2,
    )
    tester.assert_ok(r)
    body = tester.assert_json(r, dict)
    actual_pet = PetEntity.model_validate(body)
    assert expected_new_pet == actual_pet

    # after put the old old_pet name shouldn't be found
    actual_pet_after_put = await tester.get_pet(
        type_id=created_type.id, pet_name=old_pet.name
    )
    assert actual_pet_after_put == expected_new_pet

    # after put the new image should be present.
    picture = await tester.get_picture(expected_new_pet.picture)
    tester.assert_equal_images(picture, tester.example_picture_bytes2)
