from typing import Union
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import subprocess

from builelib_run import builelib_run

app = FastAPI()

@app.get("/webpro_mode")
def read_root(file_name: str):
    builelib_run(True, file_name)

# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}
