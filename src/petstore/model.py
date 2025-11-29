from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)
from starlette import status

type NoBirthdate = Literal["NA"]
type Birthdate = str | NoBirthdate

type NoPicture = Literal["NA"]
type PictureFile = str | NoPicture


class Picture(BaseModel):
    id: str
    ext: str
    type: str
    filename: str
    content: bytes
    model_config = ConfigDict(ser_json_bytes="base64")


class PetStoreModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def normalize_strings(cls, data: dict) -> dict:
        for k, v in list(data.items()):
            if isinstance(v, str):
                data[k] = v.lower()
        return data


class CreatePetTypeRequest(PetStoreModel):
    type: str


class PetTypeEntity(PetStoreModel):
    id: str
    type: str
    family: str
    genus: str
    attributes: list[str]
    lifespan: int | None
    pets: list[str]


class PetEntity(PetStoreModel):
    name: str
    picture: PictureFile = "NA"
    birthdate: Birthdate = "NA"


class CreateNewPetRequest(PetStoreModel):
    name: str
    picture_url: HttpUrl | None = Field(None, alias="picture-url")
    birthdate: str | None = None

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, v: str) -> str:
        # special “no date” marker is always allowed
        if v == "NA":
            return v

        try:
            # enforce the exact syntactic format: DD-MM-YYYY
            datetime.strptime(v, "%d-%m-%Y")  # noqa: DTZ007
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed data: birthdate must be a real date in DD-MM-YYYY",
            ) from e

        return v
