import re
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

import anyio
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from redis import WatchError
from starlette.exceptions import HTTPException as InternalHTTPException
from starlette.responses import JSONResponse

from petstore.model import (
    CreateNewPetRequest,
    CreatePetTypeRequest,
    PetEntity,
    PetTypeEntity,
    Picture,
)
from petstore.ninja import NinjaAnimals, NinjaApiError, get_ninja
from petstore.redis import get_redis

if TYPE_CHECKING:
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
        k = self._pet_types_id_key(type_id)
        return await self._backend.delete(k)

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
        pipe = self._backend.pipeline()
        pet_type_key = self._pet_types_id_key(pet_type.id)
        pet_key = self._pet_key(pet_type.id, pet_name)
        new_pet = PetEntity(
            name=pet_name,
            birthdate=birthdate or "NA",
            picture=picture_file or "NA",
        )
        new_pet_type = pet_type.model_copy()
        new_pet_type.pets.append(pet_name)
        try:
            await pipe.watch(pet_key)
            await pipe.watch(pet_type_key)
            await pipe.set(pet_key, new_pet.model_dump_json())
            await pipe.set(pet_type_key, new_pet_type.model_dump_json())
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

    async def store_picture(self, picture: Picture) -> None:
        await self._backend.setnx(picture.id, picture.model_dump_json())
        await self._backend.setnx(picture.filename, picture.id)

        async with await anyio.open_file(picture.filename, "wb") as f:
            await f.write(picture.content)

    async def get_pet(self, pet_type_id: str, pet_name: str) -> PetEntity | None:
        key = self._pet_key(type_id=pet_type_id, name=pet_name)
        p = await self._backend.get(key)
        if not p:
            return None

        return PetEntity.model_validate_json(p)


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


class PetTypeQuery(BaseModel, extra="allow"):
    family: str | None = None
    attrs: list[str] | None = Field(None, alias="hasAttribute")


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
        url = request.picture_url.encoded_string()
        pic = await storage_api.get_picture_by_url(url=url)
        if not pic:
            pic = await ninja_api.get_picture_for_pet(
                picture_url=url,
                pet_name=request.name,
                pet_type=pet_type.id,
            )
            await storage_api.store_picture(pic)
        picture_filename = pic.filename

    return await storage_api.create_new_pet(
        pet_type=pet_type,
        pet_name=request.name,
        birthdate=request.birthdate,
        picture_file=picture_filename,
    )


@app.get(PetStoreResource.PET_TYPE_ID_PETS, status_code=status.HTTP_200_OK)
async def get_pets_for_pet_type(
    type_id: str, backend: PetStoreStorageDI
) -> list[PetEntity]:
    pet_type = await backend.get_pet_type(type_id)
    if not pet_type:
        raise NotFoundError

    items: list[PetEntity] = []
    for pet_name in pet_type.pets:
        pet = await backend.get_pet(type_id, pet_name)
        assert pet
        items.append(pet)

    return items
