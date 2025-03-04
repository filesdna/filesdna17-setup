import requests
import json
from odoo import _
from odoo.tools import logging

_logger = logging.getLogger(__name__)

BLOCKCHAIN_API_URL = "https://bc2.filesdna.com/api"

class BlockchainService:

    @staticmethod
    def create_account_in_blockchain(user_id):
        """
        Create an account in the blockchain.
        :param user_id: ID of the user.
        :return: Response from the blockchain API or None on failure.
        """
        try:
            response = requests.post(
                f"{BLOCKCHAIN_API_URL}/account",
                headers={"Content-Type": "application/json"},
                json={"id": user_id}
            )
            response.raise_for_status()
            _logger.info(f"response.json():{response.json()}")
            return response.json()
        except (requests.RequestException, ValueError) as e:
            _logger.error(f"Error creating account in blockchain: {e}")
            return None

    @staticmethod
    def get_account_in_blockchain(user_id):
        """
        Retrieve an account from the blockchain.
        :param user_id: ID of the user.
        :return: Response from the blockchain API or None on failure.
        """
        if user_id == 0:
            return None

        try:
            response = requests.get(
                f"{BLOCKCHAIN_API_URL}/account/{user_id}",
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            _logger.error(f"Error fetching account from blockchain: {e}")
            return None

    @staticmethod
    def add_document_in_blockchain(data):
        """
        Add a document to the blockchain.
        :param data: Dictionary containing user_id and hash.
        :return: Response from the blockchain API or None on failure.
        """
        try:
            response = requests.post(
                f"{BLOCKCHAIN_API_URL}/document",
                headers={"Content-Type": "application/json"},
                json={"OwnerID": data.get("user_id"), "body": data.get("hash")}
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            _logger.error(f"Error adding document to blockchain: {e}")
            return None

    @staticmethod
    def get_document_in_blockchain(document_id):
        """
        Retrieve a document from the blockchain by its ID.
        :param document_id: ID of the document.
        :return: Response from the blockchain API or None on failure.
        """
        try:
            response = requests.get(
                f"{BLOCKCHAIN_API_URL}/document/{document_id}",
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            _logger.error(f"Error fetching document from blockchain: {e}")
            return None

    @staticmethod
    def add_signature_in_blockchain(data, user_id=0):
        """
        Add a signature to the blockchain.
        :param data: Dictionary containing hash data.
        :param user_id: ID of the user.
        :return: Response from the blockchain API or an empty dict if user_id is 0.
        """
        if user_id == 0:
            return {}

        try:
            response = requests.post(
                f"{BLOCKCHAIN_API_URL}/create_signature",
                headers={"Content-Type": "application/json"},
                json={"id": user_id, "payload": data}
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            _logger.error(f"Error adding signature to blockchain: {e}")
            return None

    @staticmethod
    def verify_signature_in_blockchain(data):
        """
        Verify a signature in the blockchain.
        :param data: Dictionary containing user_id, bc_document, and bc_signature_hash.
        :return: Response from the blockchain API or None on failure.
        """
        try:
            response = requests.post(
                f"{BLOCKCHAIN_API_URL}/verify_signature",
                headers={"Content-Type": "application/json"},
                json={
                    "id": data.get("user_id"),
                    "payload": json.dumps(data.get("bc_document")),
                    "signature": data.get("bc_signature_hash")
                }
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            _logger.error(f"Error verifying signature in blockchain: {e}")
            return None
