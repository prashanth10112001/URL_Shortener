from fastapi import FastAPI
from app.core.config import settings

app = FastAPI()


@app.get("/health")
def health():
    return {"message": "Hello World","base_url":settings.BASE_URL}
