# # app_package/services/blockchain_service.py
# import json
# from typing import List
# from web3 import Web3
# from web3.contract import Contract
# from web3.exceptions import ContractLogicError
# from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
# from ..config import settings
#
# import os
#
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # project root
# ABI_PATH = os.path.join(BASE_DIR, "app_package/contracts/TrueTag.json")  # adjust if you move it
#
# if not os.path.exists(ABI_PATH):
#     raise RuntimeError(f"ABI file not found at {ABI_PATH}. Please check path.")
#
# with open(ABI_PATH, "r") as f:
#     contract_abi = json.load(f)["abi"]
#
#
#
# class BlockchainService:
#     def __init__(self):
#         """Initializes the Web3 client and contract instance."""
#         self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC))
#
#         # Inject POA middleware for chains like Polygon / BSC
#         self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
#
#         if not self.w3.is_connected():
#             raise ConnectionError("Failed to connect to the blockchain RPC.")
#
#         # Load the contract
#         self.contract_address = settings.CONTRACT_ADDRESS
#         self.contract: Contract = self.w3.eth.contract(
#             address=self.contract_address, abi=contract_abi
#         )
#
#         # Admin credentials (for minting authority)
#         self.admin_wallet = settings.ADMIN_WALLET
#         self.admin_private_key = settings.ADMIN_PRIVATE_KEY
#
#     async def mint_tags_in_bulk(self, tag_codes: List[str], batch_id: int) -> str:
#         """
#         Mints a batch of tags on the blockchain.
#
#         Args:
#             tag_codes (List[str]): List of unique tag codes to mint.
#             batch_id (int): The unique ID for this batch from the database.
#
#         Returns:
#             str: The transaction hash of the minting transaction.
#
#         Raises:
#             Exception: If the transaction fails.
#         """
#         try:
#             nonce = self.w3.eth.get_transaction_count(self.admin_wallet)
#
#             # Build the transaction
#             tx = self.contract.functions.mintTagBatch(tag_codes, batch_id).build_transaction({
#                 "from": self.admin_wallet,
#                 "nonce": nonce,
#                 "gas": 2_000_000,  # adjust if too high/low
#                 "maxFeePerGas": self.w3.to_wei("50", "gwei"),
#                 "maxPriorityFeePerGas": self.w3.to_wei("2", "gwei"),
#                 "chainId": self.w3.eth.chain_id,
#             })
#
#             # Sign and send the transaction
#             signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.admin_private_key)
#             tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#
#             # Wait for confirmation
#             receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
#
#             if receipt["status"] != 1:
#                 raise RuntimeError("Blockchain transaction failed.")
#
#             return tx_hash.hex()
#
#         except ContractLogicError as e:
#             raise RuntimeError(f"Smart contract rejected transaction: {e}")
#         except Exception as e:
#             raise RuntimeError(f"Failed to mint tags: {e}")
#
#     async def mint_warehouse_batch(self, tag_codes: List[str]) -> str:
#         """
#         Mints a batch of tags to TrueTag’s admin wallet (warehouse pool).
#         """
#         nonce = self.w3.eth.get_transaction_count(self.admin_wallet)
#         tx = self.contract.functions.mintWarehouseBatch(tag_codes).build_transaction({
#             "from": self.admin_wallet,
#             "nonce": nonce,
#             "gas": 2_000_000,
#             "gasPrice": self.w3.eth.gas_price
#         })
#         signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.admin_private_key)
#         tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#         self.w3.eth.wait_for_transaction_receipt(tx_hash)
#         return tx_hash.hex()
#
#
# # Singleton instance (so we don’t reinitialize Web3 everywhere)
# blockchain_service = BlockchainService()



# app_package/services/blockchain_service.py
"""
Blockchain service integration for TrueTag.
Handles warehouse minting, direct minting, and (future) on-chain reassignment.

This is wired to the expected ABI functions:
- mintWarehouseBatch(string[] tagCodes)
- mintBatch(string[] tagCodes, uint256 manufacturerId)
- assignTagsToManufacturer(uint256[] tagIds, uint256 manufacturerId) [future]
"""

import json
import logging
from pathlib import Path
from web3 import Web3
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
from ..config import settings

logger = logging.getLogger(__name__)


class BlockchainService:
    """
    Service for interacting with the TrueTag smart contract.
    """

    def __init__(self):
        abi_path = Path(__file__).resolve().parent.parent.parent / "app_package/contracts/TrueTag.json"
        if not abi_path.exists():
            raise RuntimeError("TrueTag.json ABI file not found. Ensure it's in the project root.")

        with open(abi_path, "r") as f:
            contract_abi = json.load(f)["abi"]

        self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Blockchain RPC.")

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            abi=contract_abi
        )
        self.admin_wallet = Web3.to_checksum_address(settings.ADMIN_WALLET)
        self.admin_key = settings.ADMIN_PRIVATE_KEY

        logger.info("BlockchainService initialized successfully.")

    async def mint_warehouse_batch(self, tag_codes: list[str]) -> str:
        """
        Mint tags into the TrueTag warehouse pool (admin wallet).
        Function: mintWarehouseBatch(string[] tagCodes)
        """
        try:
            tx = self.contract.functions.mintWarehouseBatch(tag_codes).build_transaction({
                "from": self.admin_wallet,
                "nonce": self.w3.eth.get_transaction_count(self.admin_wallet),
                "gas": 3_000_000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.admin_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f"Warehouse batch minted. Tx: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Warehouse minting failed: {e}")
            raise RuntimeError(f"Warehouse minting failed: {e}")

    async def mint_tags_in_bulk(self, tag_codes: list[str], manufacturer_id: int) -> str:
        """
        Mint tags directly to a manufacturer (on-chain ownership).
        Function: mintBatch(string[] tagCodes, uint256 manufacturerId)
        """
        try:
            tx = self.contract.functions.mintBatch(tag_codes, manufacturer_id).build_transaction({
                "from": self.admin_wallet,
                "nonce": self.w3.eth.get_transaction_count(self.admin_wallet),
                "gas": 3_000_000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.admin_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f"Direct minting complete. Tx: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Direct minting failed: {e}")
            raise RuntimeError(f"Direct minting failed: {e}")

    async def assign_tags_to_manufacturer(self, tag_ids: list[int], manufacturer_id: int) -> str:
        """
        Reassign tags to a manufacturer (future upgrade).
        Function: assignTagsToManufacturer(uint256[] tagIds, uint256 manufacturerId)
        """
        try:
            tx = self.contract.functions.assignTagsToManufacturer(tag_ids, manufacturer_id).build_transaction({
                "from": self.admin_wallet,
                "nonce": self.w3.eth.get_transaction_count(self.admin_wallet),
                "gas": 3_000_000,
                "gasPrice": self.w3.eth.gas_price,
            })
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.admin_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f"Tags reassigned. Tx: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Reassignment failed: {e}")
            raise RuntimeError(f"Reassignment failed: {e}")


# Singleton instance
blockchain_service = BlockchainService()
