from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.prompt import router as prompt_router

app = FastAPI(title="Promptful")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompt_router)
