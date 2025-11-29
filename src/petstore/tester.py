from typing import TYPE_CHECKING, Any, TypeVar

from httpx import AsyncClient, Response, codes

from petstore import PetEntity, PetStoreResource, PetTypeEntity

if TYPE_CHECKING:
    from docker.models.containers import Container


class PetStoreTester:
    codes = codes

    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    @property
    def example_pet(self) -> PetEntity:
        return PetEntity(name="jamie", birthdate="24-10-2023", picture="1.jamie.jpg")

    @property
    def example_populated_pet_type(self) -> PetTypeEntity:
        return PetTypeEntity(
            id="1",
            type="Poodle",
            family="Canidae",
            genus="Canis",
            attributes=[],
            lifespan=16,
            pets=["Tony", "Lian", "Jamie"],
        )

    @property
    def example_empty_pet_type(self) -> PetTypeEntity:
        return self.example_populated_pet_type.model_copy(update={"pets": []})

    async def unsafe_get_pet_type(self, type_id: str) -> Response:
        return await self.client.get(
            PetStoreResource.PET_TYPE_ID.format(type_id=type_id)
        )

    async def unsafe_post_pet(
        self,
        *,
        type_id: str,
        name: str,
        birthdate: str | None = None,
        picture_url: str | None = None,
    ) -> Response:
        payload: dict[str, Any] = {"name": name}
        if birthdate:
            payload["birthdate"] = birthdate
        if picture_url:
            payload["picture-url"] = picture_url
        return await self.client.post(
            PetStoreResource.PET_TYPE_ID_PETS.format(type_id=type_id),
            json=payload,
        )

    async def post_new_pet_type(self, *, type_name: str) -> PetTypeEntity:
        r = await self.client.post(
            PetStoreResource.PET_TYPE,
            json={"type": type_name},
        )
        self.assert_created(r)
        p = self.assert_json(r, dict)
        return PetTypeEntity.model_validate(p)

    async def unsafe_post_pet_type(self, type_name: Any) -> Response:  # noqa: ANN401
        return await self.client.post(
            PetStoreResource.PET_TYPE, json={"type": type_name}
        )

    async def delete_pet_type(self, type_id: str) -> Response:
        return await self.client.delete(PetStoreResource.PET_TYPE_ID.format(type_id))

    async def put_pet_type(self, type_id: str, json: dict) -> Response:
        return await self.client.put(
            PetStoreResource.PET_TYPE_ID.format(type_id), json=json
        )

    async def get_pet(self, type_id: str, pet_name: str) -> Response:
        return await self.client.get(
            PetStoreResource.PET_TYPE_ID_PETS_NAME.format(id=type_id, name=pet_name)
        )

    async def get_pet_types(
        self,
        *,
        attr: str | None = None,
        family: str | None = None,
        non_sensical_query: bool | None = None,
    ) -> list[PetTypeEntity]:
        query: dict[str, str] = {}
        if family:
            query["family"] = family
        if attr:
            query["hasAttribute"] = attr
        if non_sensical_query:
            query["non_sensical_query"] = "non_sensical_query"
        r = await self.client.get(PetStoreResource.PET_TYPE, params=query)
        self.assert_ok(r)
        body = self.assert_json(r, list)
        return [PetTypeEntity.model_validate(p) for p in body]

    async def get_picture(self, file_name: str) -> Response:
        return await self.client.get(PetStoreResource.PICTURES.format(file_name))

    async def delete_pet(self, type_id: str, pet_name: str) -> Response:
        return await self.client.delete(
            PetStoreResource.PET_TYPE_ID_PETS_NAME.format(id=type_id, name=pet_name)
        )

    async def put_pet(
        self, type_id: str, pet_name: str, *, json: dict | None = None
    ) -> Response:
        return await self.client.put(
            PetStoreResource.PET_TYPE_ID_PETS_NAME.format(id=type_id, name=pet_name),
            json=json,
        )

    async def put_pet_raw(
        self,
        type_id: str,
        pet_name: str,
        *,
        raw_content: bytes,
        content_type: str,
    ) -> Response:
        return await self.client.put(
            PetStoreResource.PET_TYPE_ID_PETS_NAME.format(id=type_id, name=pet_name),
            content=raw_content,
            headers={"content-type": content_type},
        )

    def assert_status(self, r: Response, expected: int) -> None:
        assert r.status_code == expected, (
            f"{expected!r} != {r.status_code!r} (body={r.text!r})"
        )

    def assert_ok(self, r: Response) -> None:
        self.assert_status(r, self.codes.OK)

    def assert_created(self, r: Response) -> None:
        self.assert_status(r, self.codes.CREATED)

    def assert_json[T](self, r: Response, expected: type[T]) -> T:
        ctype = r.headers.get("content-type", "")
        assert ctype.startswith("application/json"), (
            f"Expected JSON response, got content-type {ctype!r}"
        )
        body = r.json()
        assert isinstance(body, expected)
        return body

    T = TypeVar("T")

    def require_key(self, obj: dict[str, Any], key: str, typ: type[T]) -> T:
        assert key in obj, f"Missing key {key!r} in JSON object {obj!r}"
        value = obj[key]
        msg = (
            f"Key {key!r} expected {typ.__name__}, "
            f"got {type(value).__name__}: {value!r}"
        )
        assert isinstance(value, typ), msg
        return value

    def assert_error(self, r: Response, msg: str) -> None:
        body = self.assert_json(r, dict)
        assert msg in body.get("error", None)

    def assert_malformed(self, r: Response) -> None:
        self.assert_status(r, self.codes.BAD_REQUEST)
        self.assert_error(r, "Malformed data")

    def assert_not_found(self, r: Response) -> None:
        self.assert_error(r, "Not Found")
        self.assert_status(r, self.codes.NOT_FOUND)

    def assert_media_type_error(self, r: Response) -> None:
        self.assert_status(r, self.codes.UNSUPPORTED_MEDIA_TYPE)
        self.assert_error(r, "Expected application/json media type")

    async def assert_only_get_allowed(self, client: AsyncClient, path: str) -> None:
        for m in ("post", "put", "patch", "delete"):
            r = await getattr(client, m)(path)
            self.assert_status(r, self.codes.METHOD_NOT_ALLOWED)
            self.assert_error(r, "Method Not Allowed")

    def assert_bad_request(self, r: Response) -> None:
        self.assert_status(r, self.codes.BAD_REQUEST)
        self.assert_error(r, "Malformed data")

    def assert_method_not_allowed(self, r: Response) -> None:
        assert r.status_code == self.codes.METHOD_NOT_ALLOWED, (
            f"Expected 405 Method Not Allowed, got {r.status_code!r}"
        )
        self.assert_error(r, "Method Not Allowed")

    def assert_picture_exists(self, file_name: str) -> None:
        raise NotImplementedError

    def assert_picture_deleted(self, file_name: str) -> None:
        raise NotImplementedError

    def get_picture_mtime(self, file_name: str) -> float:
        raise NotImplementedError

    async def unsafe_put(self, res: PetStoreResource) -> Response:
        return await self.client.put(res)

    async def unsafe_delete(self, res: PetStoreResource) -> Response:
        return await self.client.delete(res)

    async def assert_first_example_pet_type_post_created(self) -> PetTypeEntity:
        example = self.example_empty_pet_type.type
        p = await self.post_new_pet_type(type_name=example)
        assert p == self.example_empty_pet_type
        return p

    async def assert_repeating_post_pet_type_name_error(
        self, *, type_name: str
    ) -> None:
        r = await self.unsafe_post_pet_type(type_name)
        # Same pet, second time should fail.
        self.assert_malformed(r)

    async def unsafe_delete_pet_type(self, type_id: str) -> Response:
        return await self.client.delete(
            PetStoreResource.PET_TYPE_ID.format(type_id=type_id)
        )

    def assert_no_content(self, r: Response) -> None:
        assert r.status_code == codes.NO_CONTENT
        assert r.text == ""

    async def unsafe_post(self, res: PetStoreResource) -> Response:
        return await self.client.post(res)

    async def unsafe_get_pets(self, type_id: str) -> Response:
        return await self.client.get(
            PetStoreResource.PET_TYPE_ID_PETS.format(type_id=type_id)
        )

    async def get_pets(self, type_id: str) -> list[PetEntity]:
        r = await self.unsafe_get_pets(type_id)
        self.assert_ok(r)
        body = self.assert_json(r, list)
        return [PetEntity.model_validate(p) for p in body]


class PetStoreContainerTester(PetStoreTester):
    def __init__(self, container: Container, client: AsyncClient) -> None:
        super().__init__(client)
        self.container = container

    def get_picture_mtime(self, file_name: str) -> float:
        result = self.container.exec_run(f"stat -c %Y /app/pictures/{file_name}")
        return float(result.output.decode().strip())

    def assert_picture_exists(self, file_name: str) -> None:
        code = self.container.exec_run(f"test -f /app/pictures/{file_name}").exit_code
        assert code == 0, f"Picture {file_name!r} does not exist in container"

    def assert_picture_deleted(self, file_name: str) -> None:
        code = self.container.exec_run(f"test -f /app/pictures/{file_name}").exit_code
        assert code != 0, f"Picture {file_name!r} still exists in container"
