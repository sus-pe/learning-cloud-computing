import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import Depends, FastAPI
from httpx import AsyncClient
from pydantic import BaseModel, Field
from starlette import status
from starlette.responses import JSONResponse

from petstore.store.tester import PetStoreClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from starlette.requests import Request

    from petstore.store.model import PetTypeEntity

app = FastAPI()


class PurchaseRequest(BaseModel):
    purchaser: str
    pet_type: str = Field(alias="pet-type")
    store: Literal[1, 2] | None = None
    pet_name: str | None = Field(None, alias="pet-name")


class Purchase(BaseModel):
    purchase_id: str
    purchaser: str
    pet_type: str
    store: Literal[1, 2]
    pet_name: str


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> str:
    return "Hello from PetStore Orders Service."


class PetStoresGateway:
    def __init__(self, store1: PetStoreClient, store2: PetStoreClient) -> None:
        self.store1 = store1
        self.store2 = store2

    async def check_pet_type(self, pet_type_name: str) -> PetTypeEntity | None:
        pet_types = await self.store1.get_pet_types()
        for pet_type in pet_types:
            if pet_type_name == pet_type.type:
                return pet_type
        return None

    @classmethod
    @asynccontextmanager
    async def get(cls) -> AsyncGenerator[PetStoresGateway, Any]:
        async with (
            AsyncClient(base_url="http://petstore1:8000") as store1,
            AsyncClient(base_url="http://petstore2:8000") as store2,
        ):
            yield PetStoresGateway(PetStoreClient(store1), PetStoreClient(store2))


PetStoresDI = Annotated[PetStoresGateway, Depends()]


@app.get("/test-get-pet-type-by-name", status_code=status.HTTP_200_OK)
async def get_pet_type_by_name(
    pet_name: str, stores: PetStoresDI
) -> PetTypeEntity | None:
    return await stores.check_pet_type(pet_name)


@app.post("/purchases", status_code=status.HTTP_201_CREATED)
async def handle_new_purchase(
    request: PurchaseRequest, stores: PetStoresDI
) -> Purchase:
    pet_type = request.pet_type
    await stores.check_pet_type(pet_type)
    pet_name = request.pet_name if request.pet_name else "None"
    store: Literal[1, 2] = request.store if request.store else 1
    return Purchase(
        purchase_id="0",
        purchaser=request.purchaser,
        pet_type=request.pet_type,
        store=store,
        pet_name=pet_name,
    )


@app.post("/echo", status_code=status.HTTP_200_OK)
async def handle_echo(request: Request) -> JSONResponse:
    json = await request.json()
    return JSONResponse(status_code=status.HTTP_200_OK, content=json)


@app.get("/kill")
def kill_container() -> None:
    os._exit(1)
