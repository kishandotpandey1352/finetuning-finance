# src/api/main.py

from fastapi import FastAPI
import os

app = FastAPI(title=os.getenv("APP_NAME", "finance-ai-platform"))

@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": os.getenv("APP_NAME"),
        "model": os.getenv("MODEL_NAME"),
    }