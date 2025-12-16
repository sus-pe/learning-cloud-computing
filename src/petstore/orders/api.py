import os

from fastapi import FastAPI
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

app = FastAPI()

@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> str:
    return "Hello from PetStore Orders Service."

@app.post("/purchases", status_code=status.HTTP_201_CREATED)
async def handle_new_purchase(request: Request):
    pass

@app.post("/echo", status_code=status.HTTP_200_OK)
async def handle_echo(request: Request) -> JSONResponse:
    json = await request.json()
    return JSONResponse(status_code=status.HTTP_200_OK, content=json)


@app.get("/kill")
def kill_container() -> None:
    os._exit(1)
