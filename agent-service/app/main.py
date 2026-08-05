from fastapi import FastAPI

from app.routers.memory import router as memory_router


app = FastAPI(
    title="Finance AI Agent Service",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "finance-ai-agent-service",
        "version": "0.1.0",
    }


app.include_router(memory_router)