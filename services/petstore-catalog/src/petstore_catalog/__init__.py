import re
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

import anyio
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from redis import WatchError
from starlette.exceptions import HTTPException as InternalHTTPException
from starlette.responses import JSONResponse, Response

from petstore_catalog.model import (
    Birthdate,
    CreateNewPetRequest,
    CreatePetTypeRequest,
    PetEntity,
    PetsQuery,
    PetTypeEntity,
    PetTypeQuery,
    Picture,
    PictureFile,
    PutPetRequest,
)
from petstore_catalog.ninja import NinjaAnimals, NinjaApiError, get_ninja
from petstore_catalog.redis import get_redis

if TYPE_CHECKING:
    from pydantic import HttpUrl
    from redis.asyncio import Redis

app = FastAPI()


@app.exception_handler(InternalHTTPException)
async def http_exception_handler(
    _request: Request, exc: InternalHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
    )


class PetStoreStorage:
    def __init__(self, redis_backend: Redis) -> None:
        self._backend = redis_backend

    @classmethod
    def get(cls) -> PetStoreStorage:
        return PetStoreStorage(get_redis())

    @property
    def _pet_types_key(self) -> str:
        return "pet-types"

    def _pet_types_id_key(self, type_id: str) -> str:
        assert type_id
        return f"{self._pet_types_key}:{type_id}"

    async def get_pet_type(self, type_id: str) -> PetTypeEntity | None:
        k = self._pet_types_id_key(type_id)
        p = await self._backend.get(k)
        if not p:
            return None

        return PetTypeEntity.model_validate_json(p)

    async def delete_pet_type(self, type_id: str) -> int:
        """Return how many keys were deleted. 0 if none."""
        key = self._pet_types_id_key(type_id)
        async with self._backend.pipeline() as pipe:
            try:
                await pipe.watch(key)
                stored_pet_type = await pipe.get(key)
                if not stored_pet_type:
                    return 0

                pet_type = PetTypeEntity.model_validate_json(stored_pet_type)
                if len(pet_type.pets) != 0:
                    raise MalformedDataError
                pipe.multi()
                await pipe.delete(key)
                (deleted,) = await pipe.execute()
            except WatchError as e:
                raise MalformedDataError from e
            else:
                return int(deleted)

    async def create_new_pet_type(
        self,
        type_name: str,
        family: str,
        genus: str,
        attributes: list[str],
        lifespan: int | None,
    ) -> PetTypeEntity:
        pet_id = await self._get_unique_pet_type_id(type_name)
        p = PetTypeEntity(
            id=pet_id,
            type=type_name,
            family=family,
            genus=genus,
            attributes=attributes,
            lifespan=lifespan,
            pets=[],
        )
        is_set = await self._backend.setnx(
            self._pet_types_id_key(pet_id), p.model_dump_json()
        )
        if not is_set:
            # Seems like a race condition has triggered,
            # someone set the key before this.
            raise MalformedDataError

        return p

    def _pet_type_name_id_key(self, name: str) -> str:
        return f"pet-type-name-id:{name}"

    async def _get_unique_pet_type_id(self, type_name: str) -> str:
        fresh_id = str(await self._backend.incr("ids:pet-type"))
        is_set = await self._backend.setnx(
            self._pet_type_name_id_key(type_name), fresh_id
        )
        if not is_set:
            raise MalformedDataError
        return fresh_id

    async def clear(self) -> None:
        await self._backend.flushall()

    async def list_pet_types(
        self, family: str | None, attrs: list[str] | None
    ) -> list[PetTypeEntity]:
        keys = await self._backend.keys(self._pet_types_id_key("*"))
        items: list[PetTypeEntity] = []

        for key in keys:
            raw = await self._backend.get(key)
            if raw:
                items.append(PetTypeEntity.model_validate_json(raw))

        if family is not None:
            items = [x for x in items if x.family.lower() == family.lower()]

        if attrs is not None:
            for attr in attrs:
                items = [
                    x
                    for x in items
                    if attr.lower() in {a.lower() for a in x.attributes}
                ]

        return items

    async def get_type_name_id(self, type_name: str) -> str:
        return await self._backend.get(self._pet_type_name_id_key(type_name))

    async def create_new_pet(
        self,
        *,
        pet_type: PetTypeEntity,
        pet_name: str,
        birthdate: str | None,
        picture_file: str | None,
    ) -> PetEntity:
        pet_type_key = self._pet_types_id_key(pet_type.id)
        pet_key = self._pet_key(pet_type.id, pet_name)
        new_pet = PetEntity(
            name=pet_name,
            birthdate=birthdate or "NA",
            picture=picture_file or "NA",
        )
        new_pet_type = pet_type.model_copy()
        new_pet_type.pets.append(pet_name)
        async with self._backend.pipeline() as pipe:
            try:
                await pipe.watch(pet_key, pet_type_key)
                pipe.multi()
                pipe.set(pet_key, new_pet.model_dump_json())
                pipe.set(pet_type_key, new_pet_type.model_dump_json())
                await pipe.execute()
            except WatchError as e:
                # Race occurred, someone beat us to saving the name.
                # so we just tell the caller that the pet name exists.
                raise MalformedDataError from e
            else:
                return new_pet

    def _pet_key(self, type_id: str, name: str) -> str:
        assert type_id
        assert name
        type_key = self._pet_types_id_key(type_id)
        assert type_key
        return f"{type_key}:{name}"

    async def get_picture_by_url(self, url: str) -> Picture | None:
        pic = await self._backend.get(url)
        if not pic:
            return None
        return Picture.model_validate_json(pic)

    async def ensure_picture_stored(self, picture: Picture) -> None:
        await self._backend.setnx(picture.id, picture.model_dump_json())
        picture_filename_key = self._picture_filename_key(picture.filename)
        # Override ok. Picture is tied to a specific pet-entity.
        await self._backend.set(picture_filename_key, picture.id)

        async with await anyio.open_file(picture.filename, "wb") as f:
            await f.write(picture.content)

    def _picture_filename_key(self, picture: str) -> str:
        # Currently the key is just the filename, maybe will change if needed.
        return picture

    async def get_pet(self, pet_type_id: str, pet_name: str) -> PetEntity | None:
        key = self._pet_key(type_id=pet_type_id, name=pet_name)
        p = await self._backend.get(key)
        if not p:
            return None

        return PetEntity.model_validate_json(p)

    async def delete_pet(self, type_id: str, pet: PetEntity) -> None:
        pet_key = self._pet_key(type_id=type_id, name=pet.name)
        picture_filename_key = self._picture_filename_key(pet.picture)
        pet_type_key = self._pet_types_id_key(type_id)

        async with self._backend.pipeline() as pipe:
            try:
                await pipe.watch(pet_key, picture_filename_key, pet_type_key)
                raw_pet_type = await pipe.get(pet_type_key)
                pet_type = PetTypeEntity.model_validate_json(raw_pet_type)
                assert pet.name in pet_type.pets
                pet_type.pets.remove(pet.name)
                pipe.multi()
                pipe.set(pet_type_key, pet_type.model_dump_json())
                pipe.delete(picture_filename_key)
                pipe.delete(pet_key)
                await pipe.execute()
            except WatchError as e:
                raise MalformedDataError from e

    async def get_picture_by_filename(self, file_name: str) -> Picture | None:
        pic_id_key = await self._backend.get(file_name)
        if not pic_id_key:
            return None

        pic = await self._backend.get(pic_id_key)
        if not pic:
            return None

        return Picture.model_validate_json(pic)

    async def update_pet(
        self,
        type_id: str,
        old_pet: PetEntity,
        new_pet_birthdate: Birthdate,
        new_picture: PictureFile,
    ) -> PetEntity:
        """Return the updated pet entity."""
        old_pet_key = self._pet_key(type_id=type_id, name=old_pet.name)
        new_pet = PetEntity(
            name=old_pet.name,
            picture=new_picture,
            birthdate=new_pet_birthdate,
        )

        async with self._backend.pipeline() as pipe:
            try:
                await pipe.watch(old_pet_key)
                pipe.multi()
                # Update pet
                pipe.set(old_pet_key, new_pet.model_dump_json())
                await pipe.execute()
            except WatchError as e:
                raise MalformedDataError from e
            else:
                return new_pet


PetStoreStorageDI = Annotated[PetStoreStorage, Depends(PetStoreStorage.get)]


@app.get("/")
async def root() -> None:
    pass


class MalformedDataError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed data"
        )


@app.exception_handler(NinjaApiError)
async def ninja_server_error(_request: Request, exc: NinjaApiError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"server error": f"API response code {exc.response.status_code!s}"},
    )


@app.exception_handler(Exception)
async def petstore_server_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "server error": "Oops! Looks like the developers have some bugs to fix. "
            f"Request={request!r} raised Exception={exc!r}"
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    payload = await request.json()
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={"error": f"Expected application/json media type: {payload=} {exc=}"},
    )


class PetStoreResource(StrEnum):
    PICTURES = "/pictures/{file_name}"
    PET_TYPE = "/pet-types"
    PET_TYPE_ID = PET_TYPE + "/{type_id}"
    PET_TYPE_ID_PETS = PET_TYPE_ID + "/pets"
    PET_TYPE_ID_PETS_NAME = PET_TYPE_ID_PETS + "/{name}"


class NotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@app.get(PetStoreResource.PET_TYPE_ID, status_code=status.HTTP_200_OK)
async def get_pet_type_id(type_id: str, backend: PetStoreStorageDI) -> PetTypeEntity:
    p = await backend.get_pet_type(type_id)
    if not p:
        raise NotFoundError

    return p


@app.delete(PetStoreResource.PET_TYPE_ID, status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet_type_id(type_id: str, backend: PetStoreStorageDI) -> None:
    deleted = await backend.delete_pet_type(type_id)
    if deleted == 0:
        raise NotFoundError


NinjaApiDI = Annotated[NinjaAnimals, Depends(get_ninja)]


@app.post(PetStoreResource.PET_TYPE, status_code=status.HTTP_201_CREATED)
async def post_pet_type(
    payload: Annotated[CreatePetTypeRequest, Body()],
    ninja_api: NinjaApiDI,
    backend: PetStoreStorageDI,
) -> PetTypeEntity:
    type_name: str = payload.type.lower()
    if await backend.get_type_name_id(type_name):
        raise MalformedDataError

    animals: list[dict[str, Any]] = await ninja_api.get(type_name)
    if not animals:
        raise MalformedDataError

    first: dict[str, Any] = next(
        filter(lambda e: e["name"].lower() == type_name, animals)
    )

    attributes = []
    if "group_behavior" in first["characteristics"]:
        attributes = re.findall(r"\w+", first["characteristics"]["group_behavior"])
    elif "temperament" in first["characteristics"]:
        attributes = re.findall(r"\w+", first["characteristics"]["temperament"])

    lifespan = None
    if "lifespan" in first["characteristics"]:
        candidates = [
            int(n) for n in re.findall(r"\d+", first["characteristics"]["lifespan"])
        ]
        if len(candidates) >= 1:
            lifespan = min(candidates)

    family = first.get("taxonomy", {}).get("family", "")
    genus = first.get("taxonomy", {}).get("genus", "")

    return await backend.create_new_pet_type(
        type_name=type_name,
        family=family,
        genus=genus,
        attributes=attributes,
        lifespan=lifespan,
    )


@app.post(PetStoreResource.PET_TYPE, status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
async def post_pet_type_invalid_request() -> None:
    pass


@app.get(PetStoreResource.PET_TYPE)
async def list_pet_types(
    backend: PetStoreStorageDI,
    query: Annotated[PetTypeQuery, Query()],
) -> list[PetTypeEntity]:
    if query.model_extra:
        return []

    return await backend.list_pet_types(query.family, query.attrs)


@app.post("/force-clear", status_code=status.HTTP_200_OK)
async def force_clear(backend: PetStoreStorageDI) -> None:
    await backend.clear()


async def download_new_image(
    picture_url: HttpUrl,
    storage_api: PetStoreStorage,
    ninja_api: NinjaAnimals,
    pet_name: str,
    pet_type: str,
) -> str:
    """Return the generated filename."""
    url = picture_url.encoded_string()
    pic = await storage_api.get_picture_by_url(url=url)
    if not pic:
        pic = await ninja_api.get_picture_for_pet(
            picture_url=url,
            pet_name=pet_name,
            pet_type=pet_type,
        )
    await storage_api.ensure_picture_stored(pic)
    return pic.filename


@app.post(PetStoreResource.PET_TYPE_ID_PETS, status_code=status.HTTP_201_CREATED)
async def post_new_pet_to_type(
    type_id: str,
    storage_api: PetStoreStorageDI,
    ninja_api: NinjaApiDI,
    request: CreateNewPetRequest,
) -> PetEntity:
    pet_type = await storage_api.get_pet_type(type_id)
    if not pet_type:
        raise NotFoundError
    picture_filename = "NA"
    if request.picture_url:
        picture_filename = await download_new_image(
            picture_url=request.picture_url,
            storage_api=storage_api,
            ninja_api=ninja_api,
            pet_type=pet_type.id,
            pet_name=request.name,
        )
        assert picture_filename != "NA"
    return await storage_api.create_new_pet(
        pet_type=pet_type,
        pet_name=request.name,
        birthdate=request.birthdate,
        picture_file=picture_filename,
    )


@app.get(PetStoreResource.PET_TYPE_ID_PETS, status_code=status.HTTP_200_OK)
async def get_pets_for_pet_type(
    type_id: str,
    backend: PetStoreStorageDI,
    query: Annotated[PetsQuery, Query()],
) -> list[PetEntity]:
    pet_type = await backend.get_pet_type(type_id)
    if not pet_type:
        raise NotFoundError

    if query.model_extra:
        return []

    items: list[PetEntity] = []
    for pet_name in pet_type.pets:
        pet = await backend.get_pet(type_id, pet_name)
        assert pet
        items.append(pet)

    if query.birthdate_gt:
        threshold = query.get_birthdate_gt()
        assert threshold
        items = [pet for pet in items if pet.is_birthdate_gt(threshold)]

    if query.birthdate_lt:
        threshold = query.get_birthdate_lt()
        assert threshold
        items = [pet for pet in items if pet.is_birthdate_lt(threshold)]

    return items


@app.get(PetStoreResource.PET_TYPE_ID_PETS_NAME, status_code=status.HTTP_200_OK)
async def get_pet(
    type_id: str,
    name: str,
    backend: PetStoreStorageDI,
) -> PetEntity:
    pet = await backend.get_pet(type_id, name)
    if not pet:
        raise NotFoundError
    return pet


@app.delete(
    PetStoreResource.PET_TYPE_ID_PETS_NAME, status_code=status.HTTP_204_NO_CONTENT
)
async def delete_pet(type_id: str, name: str, backend: PetStoreStorageDI) -> None:
    pet = await backend.get_pet(type_id, name)
    if not pet:
        raise NotFoundError

    await backend.delete_pet(type_id=type_id, pet=pet)


@app.get(PetStoreResource.PICTURES, status_code=status.HTTP_200_OK)
async def get_pictures(file_name: str, backend: PetStoreStorageDI) -> Response:
    pic = await backend.get_picture_by_filename(file_name)
    if not pic:
        raise NotFoundError
    return Response(
        content=pic.content,
        media_type=pic.type,
    )


@app.put(PetStoreResource.PET_TYPE_ID_PETS_NAME, status_code=status.HTTP_200_OK)
async def put_on_existing_pet(
    type_id: str,
    name: str,
    backend: PetStoreStorageDI,
    ninja_api: NinjaApiDI,
    payload: Annotated[PutPetRequest, Body()],
) -> PetEntity:
    old_pet = await backend.get_pet(type_id, name)
    if not old_pet:
        raise NotFoundError

    if payload.name != name:
        raise NotFoundError

    new_birthdate = "NA"
    if payload.birthdate:
        new_birthdate = payload.birthdate

    new_picture_filename = "NA"
    if payload.picture_url:
        new_picture_filename = await download_new_image(
            picture_url=payload.picture_url,
            storage_api=backend,
            ninja_api=ninja_api,
            pet_name=payload.name,
            pet_type=type_id,
        )
        assert new_picture_filename != "NA"
    return await backend.update_pet(
        type_id=type_id,
        old_pet=old_pet,
        new_pet_birthdate=new_birthdate,
        new_picture=new_picture_filename,
    )
