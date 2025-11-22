import re
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, model_validator
from starlette.exceptions import HTTPException as InternalHTTPException
from starlette.responses import JSONResponse

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


class PetStoreModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def normalize_strings(cls, data: dict) -> dict:
        for k, v in list(data.items()):
            if isinstance(v, str):
                data[k] = v.lower()
        return data


class PetTypeCreate(PetStoreModel):
    type: str


class PetType(PetStoreModel):
    id: str
    type: str
    family: str
    genus: str
    attributes: list[str]
    lifespan: int | None
    pets: list[str]


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

    async def get_pet_type(self, type_id: str) -> PetType | None:
        k = self._pet_types_id_key(type_id)
        p = await self._backend.get(k)
        if not p:
            return None

        return PetType.model_validate_json(p)

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
    ) -> PetType:
        pet_id = await self._get_unique_pet_type_id(type_name)
        p = PetType(
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
    ) -> list[PetType]:
        keys = await self._backend.keys(self._pet_types_id_key("*"))
        items: list[PetType] = []

        for key in keys:
            raw = await self._backend.get(key)
            if raw:
                items.append(PetType.model_validate_json(raw))

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
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={"error": "Expected application/json media type"},
    )


class PetStoreResource(StrEnum):
    PICTURES = "/pictures/{file_name}"
    PET_TYPE = "/pet-types"
    PET_TYPE_ID = PET_TYPE + "/{type_id}"
    PET_TYPE_ID_PETS = PET_TYPE_ID + "/pets"
    PET_TYPE_ID_PETS_NAME = PET_TYPE_ID_PETS + "/{name}"


class NotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@app.get(PetStoreResource.PET_TYPE_ID, status_code=status.HTTP_200_OK)
async def get_pet_type_id(type_id: str, backend: PetStoreStorageDI) -> PetType:
    p = await backend.get_pet_type(type_id)
    if not p:
        raise NotFoundError

    return p


@app.delete(PetStoreResource.PET_TYPE_ID, status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet_type_id(type_id: str, backend: PetStoreStorageDI) -> None:
    deleted = await backend.delete_pet_type(type_id)
    if deleted == 0:
        raise NotFoundError


@app.post(PetStoreResource.PET_TYPE, status_code=status.HTTP_201_CREATED)
async def post_pet_type(
    payload: Annotated[PetTypeCreate, Body()],
    ninja: Annotated[NinjaAnimals, Depends(get_ninja)],
    backend: PetStoreStorageDI,
) -> PetType:
    type_name: str = payload.type.lower()
    if await backend.get_type_name_id(type_name):
        raise MalformedDataError

    animals: list[dict[str, Any]] = await ninja.get(type_name)
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
) -> list[PetType]:
    if query.model_extra:
        return []

    return await backend.list_pet_types(query.family, query.attrs)


@app.post("/force-clear", status_code=status.HTTP_200_OK)
async def force_clear(backend: PetStoreStorageDI) -> None:
    await backend.clear()
