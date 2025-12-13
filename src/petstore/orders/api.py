import os

from fastapi import FastAPI
from starlette import status

app = FastAPI()

@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> str:
    return "Hello from PetStore Orders Service."



@app.get("/kill")
def kill_container() -> None:
    os._exit(1)
