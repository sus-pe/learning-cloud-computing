import contextlib
import re
from datetime import timedelta
from os import environ
from pathlib import Path
from secrets import randbelow
from time import sleep
from typing import TYPE_CHECKING, TypeVar

import docker
import dotenv
from docker import DockerClient
from dotenv import load_dotenv
from httpx import AsyncClient, codes
from pytest import fixture
from pytest_asyncio import fixture as async_fixture

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    from docker.models.containers import Container
    from httpx import Response


from typing import Any

from httpx import Response


class PetStoreTester:
    codes = codes

    def __init__(self, container: Container, client: AsyncClient) -> None:
        self.container = container
        self.client = client
        self._example_type_id = "2"
        self._example_type_name = "Poodle"
        self._example_pet_name_map = {"2": "Jamie"}
        self._example_picture = "Jamie-poodle.jpg"

    def example_pet_type_id(self) -> str:
        return self._example_type_id

    def example_pet_type_name(self) -> str:
        return self._example_type_name

    def example_pet_name(self, type_id: str) -> str:
        return self._example_pet_name_map[type_id]

    def example_picture_name(self) -> str:
        return self._example_picture

    def random_type_name(self) -> str:
        return f"AutoType{1000 + randbelow(9000)}"

    def get_picture_mtime(self, file_name: str) -> float:
        result = self.container.exec_run(f"stat -c %Y /app/pictures/{file_name}")
        return float(result.output.decode().strip())

    async def get_pet_type(self, type_id: str) -> Response:
        return await self.client.get(f"/pet-types/{type_id}")

    async def post_pet(
        self,
        type_id: str,
        *,
        json: dict[str, object] | None = None,
        raw_content: bytes | None = None,
        content_type: str | None = None,
    ) -> Response:
        if raw_content is not None:
            headers = {}
            if content_type is not None:
                headers["content-type"] = content_type
            return await self.client.post(
                f"/pet-types/{type_id}/pets",
                content=raw_content,
                headers=headers or None,
            )
        return await self.client.post(
            f"/pet-types/{type_id}/pets",
            json=json,
        )

    async def put_pet_picture(
        self,
        type_id: str,
        name: str,
        url: str,
    ) -> Response:
        return await self.client.put(
            f"/pet-types/{type_id}/pets/{name}",
            json={"name": name, "picture-url": url},
        )

    async def get_pets(
        self,
        type_id: str,
        *,
        query: dict[str, str] | None = None,
    ) -> Response:
        return await self.client.get(
            f"/pet-types/{type_id}/pets",
            params=query,
        )

    async def post_pet_raw(
        self,
        type_id: str,
        *,
        raw_content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Response:
        return await self.client.post(
            f"/pet-types/{type_id}/pets",
            content=raw_content,
            headers={"content-type": content_type},
        )

    async def post_pet_minimal(
        self,
        type_id: str,
        name: str,
    ) -> Response:
        return await self.post_pet(type_id, json={"name": name})

    async def get_pet_type_raw(self, type_id: str) -> Response:
        return await self.client.get(f"/pet-types/{type_id}")

    async def post_pet_type(self, *, type_name: str) -> Response:
        return await self.client.post(
            "/pet-types",
            json={"type": type_name},
        )

    async def delete_pet_type(self, type_id: str) -> Response:
        return await self.client.delete(f"/pet-types/{type_id}")

    async def put_pet_type(self, type_id: str, json: dict) -> Response:
        return await self.client.put(f"/pet-types/{type_id}", json=json)

    async def get_pet(self, type_id: str, pet_name: str) -> Response:
        return await self.client.get(f"/pet-types/{type_id}/pets/{pet_name}")

    async def get_pet_types(self, *, query: dict[str, str] | None = None) -> Response:
        return await self.client.get("/pet-types", params=query)

    async def get_picture(self, file_name: str) -> Response:
        return await self.client.get(f"/pictures/{file_name}")

    async def delete_pet(self, type_id: str, pet_name: str) -> Response:
        return await self.client.delete(f"/pet-types/{type_id}/pets/{pet_name}")

    async def put_pet(
        self, type_id: str, pet_name: str, *, json: dict | None = None
    ) -> Response:
        return await self.client.put(
            f"/pet-types/{type_id}/pets/{pet_name}",
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
            f"/pet-types/{type_id}/pets/{pet_name}",
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

    def assert_json(self, r: Response) -> dict[str, Any]:
        ctype = r.headers.get("content-type", "")
        assert ctype.startswith("application/json"), (
            f"Expected JSON response, got content-type {ctype!r}"
        )
        body = r.json()
        assert isinstance(body, dict), (
            f"Expected JSON object (dict), got {type(body).__name__}: {body!r}"
        )
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

    def assert_keys(self, obj: dict[str, Any], *, required: set[str]) -> None:
        missing = required - obj.keys()
        assert not missing, f"Missing keys: {missing!r} in object {obj!r}"

    def assert_json_list(self, r: Response) -> list[Any]:
        ctype = r.headers.get("content-type", "")
        assert ctype.startswith("application/json"), (
            f"Expected JSON list, got content-type {ctype!r}"
        )
        body = r.json()
        assert isinstance(body, list), f"Expected JSON array, got {type(body).__name__}"
        return body

    def assert_json_pet_type(self, r: Response) -> None:
        obj = self.assert_json(r)
        required = {
            "id",
            "type",
            "family",
            "genus",
            "attributes",
            "lifespan",
            "pets",
        }
        self.assert_keys(obj, required=required)

        self.require_key(obj, "id", str)
        self.require_key(obj, "type", str)
        self.require_key(obj, "family", str)
        self.require_key(obj, "genus", str)

        attrs = self.require_key(obj, "attributes", list)
        for a in attrs:
            assert isinstance(a, str), f"Expected str attribute, got {a!r}"

        ls = obj["lifespan"]
        assert ls is None or isinstance(ls, int), (
            f"Expected None or int for lifespan, got {ls!r}"
        )

        pets = self.require_key(obj, "pets", list)
        for p in pets:
            assert isinstance(p, str), f"Expected str pet entry, got {p!r}"

    def assert_json_pet(self, r: Response) -> None:
        obj = self.assert_json(r)
        self.assert_keys(obj, required={"name", "birthdate", "picture"})

        self.require_key(obj, "name", str)

        birthdate = self.require_key(obj, "birthdate", str)
        if birthdate != "NA":
            ok = re.fullmatch(r"\d{2}-\d{2}-\d{4}", birthdate)
            assert ok, f"Invalid birthdate format {birthdate!r}"

        self.require_key(obj, "picture", str)

    def assert_equal_json(self, r1: Response, r2: Response) -> None:
        j1 = r1.json()
        j2 = r2.json()
        assert j1 == j2, f"JSON mismatch: {j1!r} != {j2!r}"

    def assert_image(self, r: Response) -> None:
        self.assert_status(r, self.codes.OK)
        ctype = r.headers.get("content-type")
        assert ctype in ("image/jpeg", "image/png"), (
            f"Expected image/jpeg or image/png, got {ctype!r}"
        )
        assert isinstance(r.content, (bytes, bytearray)), (
            f"Expected image bytes, got {type(r.content).__name__}"
        )

    def assert_predicate(self, r: Response, predicate: Callable[[Any], bool]) -> None:
        obj = self.assert_json(r)
        assert predicate(obj), f"Predicate failed for object {obj!r}"

    def assert_picture_exists(self, file_name: str) -> None:
        code = self.container.exec_run(f"test -f /app/pictures/{file_name}").exit_code
        assert code == 0, f"Picture {file_name!r} does not exist in container"

    def assert_picture_deleted(self, file_name: str) -> None:
        code = self.container.exec_run(f"test -f /app/pictures/{file_name}").exit_code
        assert code != 0, f"Picture {file_name!r} still exists in container"

    def assert_same_picture_bytes(self, r1: Response, r2: Response) -> None:
        assert r1.content == r2.content, "Picture bytes differ between responses"

    def assert_error(self, r: Response, msg: str) -> None:
        body = self.assert_json(r)
        expected = {"error": msg}
        assert body == expected, f"Expected {expected!r}, got {body!r}"

    def assert_error_msg_contains(self, r: Response, part: str) -> None:
        body = self.assert_json(r)
        found = any(part in str(v) for v in body.values())
        assert found, f"Expected error message containing {part!r}, got {body!r}"

    def assert_malformed(self, r: Response) -> None:
        self.assert_status(r, self.codes.BAD_REQUEST)
        self.assert_error(r, "Malformed data")

    def assert_not_found(self, r: Response) -> None:
        self.assert_status(r, self.codes.NOT_FOUND)
        self.assert_error(r, "Not found")

    def assert_media_type_error(self, r: Response) -> None:
        self.assert_status(r, self.codes.UNSUPPORTED_MEDIA_TYPE)
        self.assert_error(r, "Expected application/json media type")

    def assert_server_error(self, r: Response) -> None:
        self.assert_status(r, self.codes.INTERNAL_SERVER_ERROR)
        self.assert_error_msg_contains(r, "API response code")

    async def assert_only_get_allowed(self, client: AsyncClient, path: str) -> None:
        for m in ("post", "put", "patch", "delete"):
            r = await getattr(client, m)(path)
            self.assert_status(r, self.codes.METHOD_NOT_ALLOWED)
            self.assert_error(r, "Method Not Allowed")

    def assert_no_content(self, r: Response) -> None:
        assert r.status_code == self.codes.NO_CONTENT, (
            f"Expected 204 No Content, got {r.status_code!r} (body={r.text!r})"
        )

    def assert_bad_request(self, r: Response) -> None:
        self.assert_status(r, self.codes.BAD_REQUEST)
        self.assert_error_msg_contains(r, "")  # generic, still expressive

    def assert_method_not_allowed(self, r: Response) -> None:
        assert r.status_code == self.codes.METHOD_NOT_ALLOWED, (
            f"Expected 405 Method Not Allowed, got {r.status_code!r}"
        )
        self.assert_error(r, "Method Not Allowed")

    def assert_pet_defaults(self, r: Response) -> None:
        obj = self.assert_json(r)
        assert obj["birthdate"] == "NA", (
            f"Expected default birthdate NA, got {obj['birthdate']!r}"
        )
        assert obj["picture"] == "NA", (
            f"Expected default picture NA, got {obj['picture']!r}"
        )

    def assert_birthdate_between(
        self, pets: list[dict], lower: str, upper: str
    ) -> None:
        for p in pets:
            bd = p["birthdate"]
            assert bd == "NA" or (lower < bd < upper), (
                f"Expected {lower} < birthdate < {upper}, got {bd!r}"
            )

    def assert_birthdate_lt(self, pets: list[dict], cutoff: str) -> None:
        for p in pets:
            bd = p["birthdate"]
            assert bd != "NA", f"Expected birthdate != 'NA' for LT filter, got {bd!r}"
            assert bd < cutoff, f"Expected birthdate < {cutoff!r}, got {bd!r}"

    def assert_birthdate_gt(self, pets: list[dict], cutoff: str) -> None:
        for p in pets:
            bd = p["birthdate"]
            assert bd == "NA" or bd > cutoff, (
                f"Expected birthdate > {cutoff}, got {bd!r}"
            )

    def assert_pet_picture_endswith(self, r: Response, ext: str) -> None:
        obj = self.assert_json(r)
        picture = obj.get("picture")
        assert isinstance(picture, str), (
            f"Expected picture to be str, got {type(picture).__name__}: {picture!r}"
        )
        assert picture.endswith(ext), (
            f"Expected picture to end with {ext!r}, got {picture!r}"
        )

    def assert_pet_picture_deleted(self, picture_file: str) -> None:
        code = self.container.exec_run(f"ls /app/pictures/{picture_file}").exit_code
        assert code != 0, f"Picture {picture_file!r} still exists in container"

    def assert_pet_field_equals(self, r: Response, key: str, expected: str) -> None:
        obj = self.assert_json(r)
        value = obj.get(key)
        assert value == expected, f"Expected pet.{key!r} == {expected!r}, got {value!r}"

    def assert_pet_type_has_pets(self, r: Response) -> None:
        obj = self.assert_json(r)
        pets = obj.get("pets", [])
        assert isinstance(pets, list), f"Expected pets list, got {pets!r}"
        assert pets, "Expected pet-type to have at least one pet"

    def assert_pet_type_empty(self, r: Response) -> None:
        obj = self.assert_json(r)
        pets = obj.get("pets", [])
        assert pets == [], f"Expected no pets, got {pets!r}"

    def assert_pet_types_have_attribute(self, r: Response, attribute: str) -> None:
        items = self.assert_json_list(r)
        for t in items:
            attrs = {a.lower() for a in t.get("attributes", [])}
            assert attribute.lower() in attrs, (
                f"Expected attribute {attribute!r} in {attrs!r}"
            )

    def assert_pet_types_family_equals(self, r: Response, family: str) -> None:
        items = self.assert_json_list(r)
        for t in items:
            fam = t.get("family", "").lower()
            assert fam == family.lower(), f"Expected family {family!r}, got {fam!r}"


CONTAINER_NAME: str = "petstore-test-container"
PETSTORE_PORT_ENV_KEY: str = "PETSTORE_PORT"


@fixture(scope="session", autouse=True)
def load_env() -> None:
    load_dotenv()


@fixture(scope="session")
def petstore_port() -> int:
    return int(environ[PETSTORE_PORT_ENV_KEY])


@fixture(scope="session")
def docker_client() -> DockerClient:
    return docker.from_env()


@fixture(scope="session")
def project_root() -> Path:
    expected = Path(__file__).resolve().parent.parent.resolve()
    assert expected.is_dir(), f"Expected project root to exist {expected!r}"
    return expected


@fixture(scope="session")
def dockerfile(project_root: Path) -> Path:
    expected = project_root / "Dockerfile"
    assert expected.is_file(), f"Expected Dockerfile to exist {expected!r}"
    return expected


@fixture(scope="session")
def petstore_base_url(petstore_port: int) -> str:
    return f"http://localhost:{petstore_port}"


@fixture(scope="session")
def _petstore_container(
    docker_client: DockerClient, petstore_port: int, dockerfile: Path
) -> Generator[Container, Any]:
    with contextlib.suppress(Exception):
        prev: Container = docker_client.containers.get(CONTAINER_NAME)
        prev.kill()
        prev.remove(force=True)

    docker_client.images.build(
        path=str(dockerfile.parent), tag="petstore-test", rm=True, forcerm=True
    )

    container: Container = docker_client.containers.run(
        "petstore-test",
        detach=True,
        name=CONTAINER_NAME,
        remove=True,
        auto_remove=True,
        environment=dotenv.dotenv_values(),
        ports={f"{petstore_port}/tcp": petstore_port},
    )

    for _ in range(60):
        container.reload()
        match container.attrs["State"]["Health"]["Status"]:
            case "healthy":
                break
            case "unhealthy":
                msg = "Unhealthy container"
                raise RuntimeError(msg)
            case _:
                sleep(timedelta(milliseconds=100).total_seconds())
    else:
        msg = "Container did not become healthy"
        raise RuntimeError(msg)

    yield container

    with contextlib.suppress(Exception):
        container.kill()


@async_fixture
async def tester(
    _petstore_container: Container, petstore_base_url: str
) -> AsyncGenerator[PetStoreTester, Any]:
    async with AsyncClient(base_url=petstore_base_url, timeout=2.0) as client:
        yield PetStoreTester(_petstore_container, client)
