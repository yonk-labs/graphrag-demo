from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(title="GraphRAG Demo", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
