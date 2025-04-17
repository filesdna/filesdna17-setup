import base64
import os
import logging
from datetime import datetime
from odoo.http import request
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.tools import config

_logger = logging.getLogger(__name__)

google_bucket = config['google_bucket']
server_path = config['server_path']

class User:
    def upload_file(self, avtar, file_type="user", key=None, name=None):
        """
        Uploads a file to Google Cloud Storage.
        
        :param avtar: Base64 encoded file string.
        :param file_type: The type of the file (default: "user").
        :param key: Encryption key (optional).
        :param name: Custom name for the file (optional).
        :return: The URL of the uploaded file.
        """
        try:
            if not isinstance(avtar, str) or not avtar:
                raise ValueError("No image found")
            
            # Decode Base64 string
            base64_string = avtar
            base64_image = base64_string.split(";base64,").pop()
            mime_type = base64_string.split(";base64,")[0].lower()
            _logger.info(f"mime_type:{mime_type}")
            _logger.info(f"avtar:{avtar}")

            # Determine file extension
            if "mpeg" in mime_type and file_type == "voice":
                extension = "mp3"
            elif "png" in mime_type:
                extension = "png"
            elif "jpg" in mime_type or "jpeg" in mime_type:
                extension = "jpg"
            elif "pdf" in mime_type:
                extension = "pdf"
            elif "gif" in mime_type:
                extension = "gif"
            else:
                raise ValueError("Invalid file type")

            # Generate file name
            image_name = f"{int(datetime.now().timestamp() * 1000)}.{extension}"
            if name:
                image_name = f"{name}.{extension}"

            # Temporary file path
            temp_dir = f"{server_path}/dms_editor/static/src/temp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_path = os.path.join(temp_dir, image_name)

            # Write the file locally
            with open(temp_path, "wb") as temp_file:
                temp_file.write(base64.b64decode(base64_image))

            # Prepare Google Cloud Storage options
            db_name= request._cr.dbname
            destination_path = f"{db_name}/{file_type}/{image_name}"
            gcs_service = LocalStorageService()

            # Upload file to Google Cloud Storage
            upload_response = gcs_service.upload_file(
                temp_path, destination_path, encryption_key=key
            )

            # Clean up local file
            if os.path.exists(temp_path):
                os.remove(temp_path)

            # Return the uploaded file URL
            if upload_response.get("success"):
                file_url = destination_path
                return file_url
            else:
                raise Exception(f"Error uploading file: {upload_response.get('message')}")

        except Exception as e:
            _logger.error(f"Error uploading file: {str(e)}")
            raise e
