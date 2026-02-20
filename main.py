from typing import Union
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import subprocess

from builelib.runner import calculate, calculate_ac

app = FastAPI()

@app.get("/webpro_mode")
def read_root(file_name: str):
    calculate(file_name)

if __name__ == '__main__':
    
    file_name = "./tests/building/Builelib_inputSheet_sample_001.xlsx"
    
    calculate(file_name)
    # calculate_ac(file_name)
