from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.agents import router as agents_router
from app.routers.memory import router as memory_router
from app.routers.tools import router as tools_router
from app.routers.data import router as data_router
from app.routers.facts import router as facts_router
from app.api.treasury_demo import router as treasury_demo_router


app = FastAPI(
    title="Finance AI Agent Service",
    version="0.1.0",
)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
# Allow the local Next.js frontend to communicate with this FastAPI
# backend during development.
#
# Frontend:
#   http://localhost:3000
#   http://127.0.0.1:3000
#
# Backend:
#   http://127.0.0.1:8010
# -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "finance-ai-agent-service",
        "version": "0.1.0",
    }


# -------------------------------------------------------------------
# API Routers
# -------------------------------------------------------------------

app.include_router(memory_router)
app.include_router(agents_router)
app.include_router(tools_router)
app.include_router(data_router)
app.include_router(facts_router)

# Treasury interview demo
app.include_router(treasury_demo_router)