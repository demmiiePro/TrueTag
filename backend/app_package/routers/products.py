# app_package/routers/products.py
"""
API routes for product management.
Supports creation with image uploads, listing, retrieval, updates, and soft deletion.
"""

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from fastapi_cache.decorator import cache
import os
import uuid
from datetime import datetime

from sqlalchemy.orm import joinedload

from .. import utils, models, oauth2, database, schemas
from ..config import settings

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


@router.post("/", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),
    meta_data: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.ProductResponse:
    """
    Create a new product with image upload and metadata.

    Args:
        product (schemas.ProductCreate): Product data (name, description, category, meta_data).
        image (UploadFile): Image file (PNG/JPEG).
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user (must be manufacturer).

    Returns:
        schemas.ProductResponse: Created product with metadata and image URL.

    Raises:
        HTTPException: If user is not a manufacturer, image is invalid, or DB error occurs.
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can create products")

        # Validate and save image
    if image.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG or JPEG images allowed")

        # The save directory should be configurable
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    image_filename = f"{uuid.uuid4()}.{image.filename.split('.')[-1]}"
    image_path = os.path.join(settings.STATIC_DIR, image_filename)

    with open(image_path, "wb") as f:
        f.write(await image.read())

    # Use a Pydantic schema for validation
    try:
        product_schema = schemas.ProductCreate(
            name=name,
            description=description,
            category=category,
            meta_data=schemas.ProductMetadata.parse_raw(meta_data) if meta_data else None
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid product data: {e}")

    db_product = models.Product(
        manufacturer_id=current_user.id,
        image_url=f"/static/{image_filename}",  # Use public URL path
        **product_schema.dict()
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return schemas.ProductResponse.from_orm(db_product)


@router.get("/", response_model=List[schemas.ProductResponse])
async def list_products(
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
) -> List[schemas.ProductResponse]:
    """
    List products for the authenticated manufacturer with optional filters.

    Args:
        status (str, optional): Filter by status (active, inactive, draft).
        category (str, optional): Filter by category.
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user (must be manufacturer).

    Returns:
        List[schemas.ProductResponse]: List of products with tags.

    Raises:
        HTTPException: If user is not a manufacturer.
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can list products")

    query = select(models.Product).where(models.Product.manufacturer_id == current_user.id)
    if status:
        query = query.where(models.Product.status == status)
    if category:
        query = query.where(models.Product.category == category)

    # Use joinedload to avoid the N+1 problem when returning products with tags.
    # NOTE: The schema has been refactored to remove the tags field for better
    # general-purpose use, so this joinedload is no longer needed unless a
    # new schema with tags is defined specifically for this endpoint.
    result = await db.execute(query)
    products = result.scalars().all()

    return [schemas.ProductResponse.from_orm(product) for product in products]


@router.get("/{id}", response_model=schemas.ProductResponse)
async def get_product(
    id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.ProductResponse:
    """
    Retrieve a single product with related tags.

    Args:
        id (int): Product ID.
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user (must be manufacturer).

    Returns:
        schemas.ProductResponse: Product details with tags.

    Raises:
        HTTPException: If product not found or not owned by user.
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can view products")

    result = await db.execute(
        select(models.Product)
        .where(models.Product.id == id, models.Product.manufacturer_id == current_user.id)
        .options(joinedload(models.Product.tags))
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or not owned")

    return schemas.ProductResponse.from_orm(product)


@router.put("/{id}", response_model=schemas.ProductResponse)
async def update_product(
    id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    meta_data: Optional[str] = Form(None),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.ProductResponse:
    """
    Update product details or image.

    Args:
        id (int): Product ID.
        product (schemas.ProductCreate): Updated product data.
        image (UploadFile, optional): New image file (PNG/JPEG).
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user (must be manufacturer).

    Returns:
        schemas.ProductResponse: Updated product details.

    Raises:
        HTTPException: If product not found, not owned, or image is invalid.
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can update products")

        # Fetch product
    result = await db.execute(
        select(models.Product).where(models.Product.id == id, models.Product.manufacturer_id == current_user.id)
    )
    db_product = result.scalars().first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or not owned")

    # Handle image update
    if image:
        if image.content_type not in ["image/png", "image/jpeg"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG or JPEG images allowed")

        # Delete old image if it exists
        if db_product.image_url and os.path.exists(db_product.image_url):
            os.remove(db_product.image_url)

        # Save new image
        image_filename = f"{uuid.uuid4()}.{image.filename.split('.')[-1]}"
        image_path = os.path.join(settings.STATIC_DIR, image_filename)
        with open(image_path, "wb") as f:
            f.write(await image.read())
        db_product.image_url = f"/static/{image_filename}"  # Public URL

    # Handle other data updates
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if category is not None:
        update_data["category"] = category
    if meta_data is not None:
        update_data["meta_data"] = schemas.ProductMetadata.parse_raw(meta_data).dict()

    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)

    return schemas.ProductResponse.from_orm(db_product)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
        id: int,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
):

    """
    Soft delete a product by setting status to inactive.

    Args:
        id (int): Product ID.
        db (AsyncSession): Database session for async operations.
        current_user (models.User): Authenticated user (must be manufacturer).

    Raises:
        HTTPException: If product not found or not owned.
    """
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can delete products")

    result = await db.execute(
        select(models.Product)
        .where(models.Product.id == id, models.Product.manufacturer_id == current_user.id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or not owned")

    product.status = "inactive"
    await db.commit()