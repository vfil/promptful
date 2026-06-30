import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.prompt import PromptVersion
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptVersionRead

router = APIRouter(prefix="/prompt", tags=["prompt"])


async def _highest_version(db: AsyncSession, slug: str) -> PromptVersion | None:
    """The row at MAX(version) for a slug — may or may not be a Tombstone. See CONTEXT.md."""
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.slug == slug)
        .order_by(PromptVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_by_id(db: AsyncSession, version_id: uuid.UUID) -> PromptVersion:
    result = await db.execute(select(PromptVersion).where(PromptVersion.id == version_id))
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no prompt version with that id")
    return version


async def _require_live(db: AsyncSession, target: PromptVersion) -> None:
    """ADR-0003: {id} must be its slug's current Live Version, or the write is stale."""
    current = await _highest_version(db, target.slug)
    if current is None or current.id != target.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "this version is no longer the current version of its slug; re-read it and retry",
        )


async def _insert_version(db: AsyncSession, version: PromptVersion) -> PromptVersion:
    db.add(version)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "a concurrent write landed on this slug first; re-read and retry",
        ) from exc
    await db.refresh(version)
    return version


@router.post("/create", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate, db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    current = await _highest_version(db, payload.slug)
    if current is not None and not current.is_deleted:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"slug '{payload.slug}' already has a live version; "
            f"use POST /prompt/{{id}} to update it",
        )
    next_version = current.version + 1 if current is not None else 1
    new_version = PromptVersion(slug=payload.slug, version=next_version, text=payload.text)
    return await _insert_version(db, new_version)


@router.post("/{id}", response_model=PromptVersionRead)
async def update_prompt(
    id: uuid.UUID, payload: PromptUpdate, db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    target = await _get_by_id(db, id)
    await _require_live(db, target)
    new_version = PromptVersion(slug=target.slug, version=target.version + 1, text=payload.text)
    return await _insert_version(db, new_version)


@router.delete("/{id}", response_model=PromptVersionRead)
async def delete_prompt(id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PromptVersion:
    target = await _get_by_id(db, id)
    await _require_live(db, target)
    tombstone = PromptVersion(
        slug=target.slug, version=target.version + 1, text="", is_deleted=True
    )
    return await _insert_version(db, tombstone)


@router.get("/{id}", response_model=PromptVersionRead)
async def get_prompt_by_id(id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PromptVersion:
    return await _get_by_id(db, id)


@router.get("", response_model=PromptVersionRead)
async def get_prompt_by_slug(
    slug: str = Query(...),
    version: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> PromptVersion:
    if version is not None:
        result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.slug == slug, PromptVersion.version == version
            )
        )
        found = result.scalar_one_or_none()
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such slug/version")
        return found

    current = await _highest_version(db, slug)
    if current is None or current.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "slug has no live version")
    return current
