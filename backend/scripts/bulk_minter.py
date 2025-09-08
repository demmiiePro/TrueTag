# scripts/bulk_minter.py
import os
import sys
import asyncio
import argparse
from typing import List
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app_package.database import AsyncSessionLocal
from app_package import models
from app_package.services.blockchain_service import blockchain_service


async def generate_tag_codes(count: int) -> List[str]:
    """Generates a list of unique UUID-based tag codes."""
    return [str(uuid4()) for _ in range(count)]


async def bulk_mint_and_store(count: int, manufacturer_id: int = 1):
    """
    1. Generates tags and a batch record in the database.
    2. Calls the blockchain service to mint the tags.
    3. Updates the database with the blockchain transaction hash.
    """
    async with AsyncSessionLocal() as db:
        tag_codes = await generate_tag_codes(count)

        # Step 1: Create a batch record
        batch_record = models.Batch(
            count=count,
            status="pending",
            manufacturer_id=manufacturer_id  # could tie to a specific manufacturer later
        )
        db.add(batch_record)
        await db.flush()  # get batch ID

        print(f"[INFO] Minting {count} tags for batch ID {batch_record.id}...")

        try:
            # Step 2: Mint on blockchain
            tx_hash = await blockchain_service.mint_tags_in_bulk(tag_codes, batch_record.id)
            batch_record.blockchain_tx_hash = tx_hash
            batch_record.status = "minted"

            print(f"[SUCCESS] Tags minted! Transaction hash: {tx_hash}")

            # Step 3: Store tag records in DB
            tag_records = [
                models.Tag(
                    tag_code=code,
                    token_id=f"TOKEN_{uuid4()}",
                    blockchain_tx_hash=tx_hash,
                    status="unused",
                    batch_id=batch_record.id,
                )
                for code in tag_codes
            ]
            db.add_all(tag_records)
            await db.commit()

            print(f"[SUCCESS] Stored {count} tags for batch {batch_record.id} in DB.")

        except Exception as e:
            await db.rollback()
            batch_record.status = "failed"
            print(f"[ERROR] Minting failed for batch {batch_record.id}: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Bulk mint TrueTag codes and store them in the database."
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        required=True,
        help="Number of tags to mint in this batch"
    )
    parser.add_argument(
        "--manufacturer", "-m",
        type=int,
        default=1,
        help="Manufacturer ID to associate with this batch (default: 1)"
    )

    args = parser.parse_args()

    # Run async task
    asyncio.run(bulk_mint_and_store(args.count, args.manufacturer))


if __name__ == "__main__":
    # Ensure DB URL is set (for standalone runs outside FastAPI)
    if not os.environ.get("ASYNC_DB_URL"):
        os.environ["ASYNC_DB_URL"] = "postgresql+asyncpg://user:password@localhost:5432/db"

    main()
