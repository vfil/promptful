import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.category import Category
from app.models.prompt import PromptVersion
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptVersionRead

router = APIRouter(prefix="/prompt", tags=["prompt"])

_WITH_CATEGORY = selectinload(PromptVersion.category)


async def _highest_version(
    db: AsyncSession, leaf_slug: str, category_id: uuid.UUID
) -> PromptVersion | None:
    """The row at MAX(version) for a (leaf_slug, category_id) — may be a Tombstone."""
    result = await db.execute(
        select(PromptVersion)
        .options(_WITH_CATEGORY)
        .where(
            PromptVersion.leaf_slug == leaf_slug,
            PromptVersion.category_id == category_id,
        )
        .order_by(PromptVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_by_id(db: AsyncSession, version_id: uuid.UUID) -> PromptVersion:
    result = await db.execute(
        select(PromptVersion)
        .options(_WITH_CATEGORY)
        .where(PromptVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no prompt version with that id")
    return version


async def _require_live(db: AsyncSession, target: PromptVersion) -> None:
    """ADR-0003: {id} must be its prompt's current Live Version, or the write is stale."""
    current = await _highest_version(db, target.leaf_slug, target.category_id)
    if current is None or current.id != target.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "this version is no longer the current version; re-read it and retry",
        )


async def _insert_version(db: AsyncSession, version: PromptVersion) -> PromptVersion:
    db.add(version)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "a concurrent write landed on this prompt first; re-read and retry",
        ) from exc
    # Re-query so the returned object has the category relationship loaded.
    result = await db.execute(
        select(PromptVersion)
        .options(_WITH_CATEGORY)
        .where(PromptVersion.id == version.id)
    )
    return result.scalar_one()


@router.post("/create", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate, db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    # Verify the category exists.
    cat_result = await db.execute(
        select(Category).where(Category.id == payload.category_id)
    )
    if cat_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "category not found")

    current = await _highest_version(db, payload.leaf_slug, payload.category_id)
    if current is not None and not current.is_deleted:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"a prompt '{payload.leaf_slug}' already exists in this category; "
            f"use POST /prompt/{{id}} to update it",
        )
    next_version = current.version + 1 if current is not None else 1
    new_version = PromptVersion(
        leaf_slug=payload.leaf_slug,
        category_id=payload.category_id,
        version=next_version,
        text=payload.text,
    )
    return await _insert_version(db, new_version)


@router.post("/{id}", response_model=PromptVersionRead)
async def update_prompt(
    id: uuid.UUID, payload: PromptUpdate, db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    target = await _get_by_id(db, id)
    await _require_live(db, target)
    new_version = PromptVersion(
        leaf_slug=target.leaf_slug,
        category_id=target.category_id,
        version=target.version + 1,
        text=payload.text,
    )
    return await _insert_version(db, new_version)


@router.delete("/{id}", response_model=PromptVersionRead)
async def delete_prompt(id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PromptVersion:
    target = await _get_by_id(db, id)
    await _require_live(db, target)
    tombstone = PromptVersion(
        leaf_slug=target.leaf_slug,
        category_id=target.category_id,
        version=target.version + 1,
        text="",
        is_deleted=True,
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
    # Resolve slug → (category_path, leaf_slug).
    last_slash = slug.rfind("/")
    if last_slash <= 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such slug/version")
    category_path = slug[:last_slash]
    leaf_slug = slug[last_slash + 1:]

    cat_result = await db.execute(
        select(Category).where(Category.path == category_path)
    )
    category = cat_result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such slug/version")

    if version is not None:
        result = await db.execute(
            select(PromptVersion)
            .options(_WITH_CATEGORY)
            .where(
                PromptVersion.leaf_slug == leaf_slug,
                PromptVersion.category_id == category.id,
                PromptVersion.version == version,
            )
        )
        found = result.scalar_one_or_none()
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no such slug/version")
        return found

    current = await _highest_version(db, leaf_slug, category.id)
    if current is None or current.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "slug has no live version")
    return current
