import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.routers.category import router as category_router
from app.routers.prompt import prompts_router, router as prompt_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Promptful")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(category_router)
app.include_router(prompt_router)
app.include_router(prompts_router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Full traceback on purpose: the response body stays generic (this
        # endpoint is unauthenticated), so the log is the only place to debug.
        logger.exception("health check failed")
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok"})
