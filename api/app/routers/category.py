import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.path))
    return list(result.scalars().all())


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate, db: AsyncSession = Depends(get_db)
) -> Category:
    if payload.parent_id is not None:
        result = await db.execute(
            select(Category).where(Category.id == payload.parent_id)
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "parent category not found")
        path = f"{parent.path}/{payload.slug_segment}"
    else:
        path = f"/{payload.slug_segment}"

    category = Category(
        slug_segment=payload.slug_segment,
        parent_id=payload.parent_id,
        path=path,
    )
    db.add(category)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"a category with slug_segment '{payload.slug_segment}' already exists "
            f"under the same parent",
        ) from exc
    await db.refresh(category)
    return category
