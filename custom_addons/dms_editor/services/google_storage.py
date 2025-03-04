from google.cloud import storage
from google.oauth2 import service_account
import base64
import logging
from datetime import datetime, timedelta
from odoo.tools import config

_logger = logging.getLogger(__name__)

google_bucket = config['google_bucket']

class LocalStorageService:
    def __init__(self):
        # Initialize storage client with credentials
        credentials = service_account.Credentials.from_service_account_file('/opt/filesdna17/custom_addons/google_cloud_storage/google_creds.json')
        self.client = storage.Client(credentials=credentials)
        self.bucket = self.client.bucket(google_bucket)

    def upload_file(self, filename, destination, encryption_key):
        try:
            blob = self.bucket.blob(destination)
            
            # Apply encryption key if provided
            if encryption_key:
                _logger.info(f"encryption:{encryption_key}")
                _logger.info(f"fix_base64_key:{self.fix_base64_key(encryption_key)}")
                encryption_key = self.fix_base64_key(encryption_key)
                blob._encryption_key = base64.b64decode(encryption_key)

            # Upload the file to the specified destination
            blob.upload_from_filename(filename)
            _logger.info(f"File {filename} uploaded to {destination} with encryption.")
            return {"success": True, "message": "Upload successful"}
        except Exception as e:
            _logger.error(f"Error uploading file: {str(e)}")
            return {"success": False, "message": str(e)}

    def download_file(self, blob_name, destination, encryption_key=None):
        try:
            blob = self.bucket.blob(blob_name)
            if encryption_key:
                _logger.info(f"encryption:{encryption_key}")
                encryption_key = self.fix_base64_key(encryption_key)
                blob._encryption_key = base64.b64decode(encryption_key)
            blob.download_to_filename(destination)
        except Exception as e:
            _logger.error(f"Error downloading file: {str(e)}")
            raise


    def delete_file(self, blob_name):
        """Delete a file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            _logger.info(f"File {blob_name} deleted from Google Cloud Storage.")
            return {"success": True, "message": "Delete successful"}
        except Exception as e:
            _logger.error(f"Error deleting file: {str(e)}")
            return {"success": False, "message": str(e)}


    def read_url(self, file_path):
        """
        Get a signed URL from Google Cloud Storage for reading a file.
        
        :param file_path: str - The file path of the file in the bucket.
        :return: str - The signed URL.
        """
        try:
            # Check if file_path is already a URL
            # if file_path.startswith("http://") or file_path.startswith("https://"):
            #     _logger.info(f"File path is already a URL: {file_path}")
            #     return file_path
            
            # Generate signed URL for valid file paths in the bucket
            blob = self.bucket.blob(file_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=128),
                method="GET"
            )
            return url

        except Exception as e:
            _logger.error(f"Error reading file: {str(e)}")
            return {"success": False, "message": str(e)}

    def fix_base64_key(self, key):
        # Make sure it's URL-safe and properly padded
        try:
            # Replace URL-safe characters
            key = key.replace('-', '+').replace('_', '/')
            # Add padding if required
            padding = 4 - (len(key) % 4)
            if padding:
                key += '=' * padding
            # Validate the key
            return key  # Return fixed key
        except Exception as e:
            raise ValueError(f"Invalid Base64 key: {str(e)}")