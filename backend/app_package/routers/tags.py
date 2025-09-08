# app_package/routers/tags.py
"""
API routes for assigning and verifying tags.
Models the business process where TrueTag mints in bulk and manufacturers are assigned pre-minted tags.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from web3 import Web3
from web3.exceptions import ContractLogicError
from ..services.blockchain_service import blockchain_service

from .. import models, oauth2, database, schemas
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tags",
    tags=["Tags"]
)

# Initialize Web3 and smart contract instance
try:
    w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Blockchain RPC.")

    with open("TrueTag.json", "r") as f:
        contract_abi = json.load(f)["abi"]

    contract = w3.eth.contract(address=settings.CONTRACT_ADDRESS, abi=contract_abi)
except (ConnectionError, FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Failed to initialize blockchain connection: {e}")
    contract = None

# --- New Admin Endpoints ---

@router.post("/mint/warehouse", response_model=schemas.BatchResponse)
async def mint_warehouse_tags(
        request: schemas.TagGenerationRequest,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_admin)
):
    """
    Mint a batch of tags into the TrueTag warehouse pool.
    Admin-only.
    """
    if request.mint_type != "warehouse":
        raise HTTPException(status_code=400, detail="mint_type must be 'warehouse' for this endpoint.")

    # Generate tag codes
    from uuid import uuid4
    tag_codes = [str(uuid4()) for _ in range(request.count)]

    batch = models.Batch(
        count=request.count,
        status="pending",
        product_id=None,
        manufacturer_id=current_user.id,  # stored as admin
        mint_type="warehouse"
    )
    db.add(batch)
    await db.flush()

    try:
        tx_hash = await blockchain_service.mint_warehouse_batch(tag_codes)
        batch.blockchain_tx_hash = tx_hash
        batch.status = "minted"

        tags = [
            models.Tag(
                tag_code=code,
                token_id=f"TOKEN_{uuid4()}",
                blockchain_tx_hash=tx_hash,
                status="unused",
                batch_id=batch.id
            )
            for code in tag_codes
        ]
        db.add_all(tags)
        await db.commit()
        await db.refresh(batch)
        return batch
    except Exception as e:
        await db.rollback()
        batch.status = "failed"
        raise HTTPException(status_code=500, detail=f"Minting failed: {str(e)}")


@router.post("/mint/direct", response_model=schemas.BatchResponse)
async def mint_direct_tags(
        request: schemas.TagGenerationRequest,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_admin)
):
    """
    Mint tags directly for a specific manufacturer (on-chain ownership).
    Admin-only.
    """
    if request.mint_type != "direct" or not request.product_id:
        raise HTTPException(status_code=400, detail="mint_type must be 'direct' and product_id is required.")

    from uuid import uuid4
    tag_codes = [str(uuid4()) for _ in range(request.count)]

    batch = models.Batch(
        product_id=request.product_id,
        count=request.count,
        status="pending",
        manufacturer_id=current_user.id,
        mint_type="direct"
    )
    db.add(batch)
    await db.flush()

    try:
        tx_hash = await blockchain_service.mint_tags_in_bulk(tag_codes, request.product_id)
        batch.blockchain_tx_hash = tx_hash
        batch.status = "minted"

        tags = [
            models.Tag(
                tag_code=code,
                token_id=f"TOKEN_{uuid4()}",
                blockchain_tx_hash=tx_hash,
                status="active",
                batch_id=batch.id,
                product_id=request.product_id
            )
            for code in tag_codes
        ]
        db.add_all(tags)
        await db.commit()
        await db.refresh(batch)
        return batch
    except Exception as e:
        await db.rollback()
        batch.status = "failed"
        raise HTTPException(status_code=500, detail=f"Direct minting failed: {str(e)}")


# --- API Endpoints ---

@router.post("/generate", status_code=status.HTTP_200_OK, response_model=schemas.BatchAssignmentResponse)
async def assign_tags_to_product(
        product_id: int,
        count: int,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
) -> schemas.BatchAssignmentResponse:
    """
    Assigns a batch of pre-minted tags to a product.

    Args:
        product_id (int): The ID of the product to assign tags to.
        count (int): The number of tags to assign.

    Returns:
        schemas.BatchAssignmentResponse: A summary of the assignment.

    Raises:
        HTTPException: If the user is not a manufacturer, the product is not owned, or not enough tags are available.
    """
    # 1. Role and Product Ownership Check
    if current_user.role != "manufacturer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only manufacturers can generate tags.")

    product_query = await db.execute(
        select(models.Product).where(
            models.Product.id == product_id,
            models.Product.manufacturer_id == current_user.id
        )
    )
    product = product_query.scalars().first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or not owned by manufacturer.")

    # 2. Find available pre-minted tags
    # Tags with status 'unused' are a pool for all manufacturers.
    available_tags_query = await db.execute(
        select(models.Tag)
        .where(models.Tag.status == "unused")
        .limit(count)
    )
    available_tags = available_tags_query.scalars().all()

    if len(available_tags) < count:
        logger.error(f"Not enough unused tags available. Requested: {count}, Available: {len(available_tags)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough tags available. Only {len(available_tags)} tags are in stock. Please contact TrueTag admin."
        )

    # 3. Assign tags and update the database
    assigned_tag_codes = [tag.tag_code for tag in available_tags]

    # We update the tags in a single batch query for efficiency
    await db.execute(
        update(models.Tag)
        .where(models.Tag.tag_code.in_(assigned_tag_codes))
        .values(product_id=product.id, status="active")
    )

    await db.commit()

    return {"message": f"Successfully assigned {len(available_tags)} tags to product '{product.name}' (ID: {product_id}).", "assigned_tag_codes": assigned_tag_codes}


@router.get("/verify/{tag_code}", response_model=schemas.VerificationResponse)
async def verify_tag(
        tag_code: str,
        location: Optional[str] = None,
        db: AsyncSession = Depends(database.get_db)
) -> schemas.VerificationResponse:
    """
    Verify a tag by checking the database and the blockchain.
    """
    # 1. Fetch tag from DB first for speed
    tag_query = await db.execute(
        select(models.Tag)
        .where(models.Tag.tag_code == tag_code)
        .options(joinedload(models.Tag.product))
    )
    tag = tag_query.scalars().first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found.")

    # 2. Check tag status in the database
    verification_result = "valid"
    if tag.status in ["unused", "flagged"]:
        verification_result = "invalid"

    # 3. Perform the critical on-chain verification
    if verification_result == "valid" and contract:
        try:
            # Check the owner of the NFT token. Should be the brand's wallet address.
            token_owner = contract.functions.ownerOf(int(tag.token_id)).call()
            expected_owner = w3.to_checksum_address(settings.ADMIN_WALLET)

            if token_owner != expected_owner:
                verification_result = "tampered"
                logger.warning(f"Tag {tag_code} tampered. Owner mismatch: expected {expected_owner}, got {token_owner}")

        except ContractLogicError as e:
            verification_result = "invalid"
            logger.warning(f"Fake tag scan detected for {tag_code}: {e}")
        except Exception as e:
            verification_result = "blockchain_error"
            logger.error(f"Blockchain verification failed for {tag_code}: {e}")

    # 4. Record the scan attempt
    scan = models.Scan(
        tag_id=tag.id,
        user_id=None,
        location=location,
        verification_result=verification_result
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # 5. Return the full response
    return schemas.VerificationResponse(
        tag_id=tag.id,
        tag_code=tag.tag_code,
        verification_result=verification_result,
        product_name=tag.product.name,
        product_image_url=tag.product.image_url
    )

