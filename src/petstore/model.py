from datetime import datetime
from typing import Literal, Self

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
    model_config = ConfigDict(ser_json_bytes="base64", val_json_bytes="base64")


class PetStoreModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def normalize_strings(cls, data: dict) -> dict:
        for k, v in list(data.items()):
            if isinstance(v, str):
                data[k] = v.lower()
        return data

    @classmethod
    def _validate_date(cls, v: str | None) -> str | None:
        if not v or v == "NA":
            return v
        try:
            cls.parse_datetime(v)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed data: birthdate must be a real date in DD-MM-YYYY",
            ) from e

        return v

    @classmethod
    def parse_datetime(cls, v: str) -> datetime:
        # enforce the exact syntactic format: DD-MM-YYYY
        return datetime.strptime(v, "%d-%m-%Y")  # noqa: DTZ007


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
    model_config = ConfigDict(extra="allow")

    def get_birthdate(self) -> datetime | None:
        if self.birthdate == "NA":
            return None

        return self.parse_datetime(self.birthdate)

    def is_birthdate_gt(self, other: datetime) -> bool:
        birthdate = self.get_birthdate()
        if not birthdate:
            return False

        return birthdate > other

    def is_birthdate_lt(self, other: datetime) -> bool:
        birthdate = self.get_birthdate()
        if not birthdate:
            return False

        return birthdate < other


class CreateNewPetRequest(PetStoreModel):
    name: str
    picture_url: HttpUrl | None = Field(None, alias="picture-url")
    birthdate: str | None = None

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, v: str | None) -> str:
        return cls._validate_date(v)


class PetsQuery(PetStoreModel):
    birthdate_gt: str | None = Field(None, alias="birthdateGT")
    birthdate_lt: str | None = Field(None, alias="birthdateLT")
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="after")
    def validate_birthdate(self) -> Self:
        self._validate_date(self.birthdate_gt)
        self._validate_date(self.birthdate_lt)
        return self

    def get_birthdate_gt(self) -> datetime | None:
        if not self.birthdate_gt:
            return None
        assert self.birthdate_gt
        return self.parse_datetime(self.birthdate_gt)

    def get_birthdate_lt(self) -> datetime | None:
        if not self.birthdate_lt:
            return None
        assert self.birthdate_lt
        return self.parse_datetime(self.birthdate_lt)


class PetTypeQuery(PetStoreModel, extra="allow"):
    family: str | None = None
    attrs: list[str] | None = Field(None, alias="hasAttribute")


class PutPetRequest(PetStoreModel):
    name: str
    birthdate: str | None = None
    picture_url: HttpUrl | None = Field(None, alias="picture-url")
