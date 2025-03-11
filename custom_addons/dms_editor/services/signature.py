import base64
import hashlib
import logging
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from odoo import http
from odoo.http import request, Response
from io import BytesIO
from odoo.tools import config
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.user import User

_logger = logging.getLogger(__name__)

 
server_path = config['server_path']

key_file = f"{server_path}/google_cloud_storage/google_creds.json"
gcs = LocalStorageService()

class SignatureHelper:

    def create_or_update_signature(self,data):
        """Create or update a user signature."""
        if not data:
            return {}

        signature = request.env['user.signature'].sudo().search([('full_name', '=', data['full_name'])], limit=1)
        if not signature:
            return request.env['user.signature'].sudo().create(data)
        else:
            signature.write(data)
            return signature


    def get_user_default_signature(self,user_id):
        """Retrieve the default signature for a user."""
        signature = request.env['user.signature'].sudo().search([('user_id', '=', user_id), ('default', '=', 1)], limit=1)

        if signature:
            if signature.full_signature:
                signature.full_signature = gcs.read_url(signature.full_signature)
            if signature.initial_signature:
                signature.initial_signature = gcs.read_url(signature.initial_signature)
        return signature


    def generate_html_signature_base64(self, image_data, hash_key, sign_type, sign_by, date, reason, no_design):
        """Generate a base64 image of an HTML signature."""
        try:
            from imgkit import from_string

            no_design = True if no_design == '0' else False

            # Define dimensions
            width = 550 if sign_type == "full" else 200
            height = 300 if sign_type == "full" else 150

            s_b = "" if not sign_by else f"""
                    <div style="margin-bottom: 10px;">
                        <span style="
                            font-size: 20px;
                            font-weight: 700;
                            white-space: nowrap;
                        ">
                            <span style="margin-right: 5px;">Signed by:</span>
                            <span style="
                                white-space: nowrap;
                                text-overflow: ellipsis;
                                overflow: hidden;
                                width: 300px;
                                display: inline-block;
                            ">{sign_by}</span>
                        </span>
                    </div>
                    """

            # Define the HTML structure
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        margin: 0;
                        padding: 0;
                        height: {height}px;
                        width: {width}px;
                    }}
                </style>
            </head>
            <body>
                <div style="
                    padding: 15px;
                    border-left: {0 if no_design else 3}px solid #0db8ad;
                    border-radius: 12px;
                    position: relative;
                    overflow: hidden;
                    height: 100%;
                    width: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    box-sizing: border-box;
                ">
                    {s_b}

                    <div style="text-align: center;margin:20px 0px 20px 0px"> <!-- Signature Image -->
                        <img alt="Signature" src="{image_data}" style="max-width: 100%; max-height: 100%;"/>
                    </div>
                    <div style="
                        margin-left: 15px; 
                        font-size: 30px;
                        display: flex;
                        flex-direction: column;
                        gap: 10px; /* Spacing between each text */
                    ">
                        {f"<span>{date}</span>" if date else ""}
                        {f"<span>{reason}</span>" if reason else ""}
                        {f"<span style='font-size: 28px;display: inline-block;width: 300px;font-weight: 600;white-space: nowrap;text-overflow: ellipsis;overflow: hidden;'>{hash_key}</span>" if sign_type == "full" else ""}
                    </div>
                </div>
            </body>
            </html>
            """

            # Convert the HTML to an image
            options = {
                "format": "png",
                "encoding": "UTF-8",
                "width": width,
                "height": height,
                "zoom": 1.0,  # Control scaling
		"transparent": "",
            }
            image_binary = from_string(html, False, options=options)

            # Encode image as Base64
            base64_image = base64.b64encode(image_binary).decode("utf-8")
            return f"data:image/png;base64,{base64_image}"

        except Exception as e:
            _logger.error(f"Error generating HTML signature base64: {str(e)}")
            raise

        
    def upload_signature(self, name, font_path, sign_type, sign_by="", date="", reason="", no_design=0, base64_output=False):
        """Generate and upload a signature."""
        try:
            # Generate text-based image
            font = ImageFont.truetype(font_path, 110)
            image = Image.new("RGBA", (700, 200), (255, 255, 255, 0))
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), name, font=font, fill="black")
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()

            # Generate the HTML for the signature
            hash_key = hashlib.sha512(image_base64.encode()).hexdigest() if sign_type == "full" else ""
            html_signature = self.generate_html_signature_base64(
                image_data=f"data:image/png;base64,{image_base64}",
                hash_key=hash_key,
                sign_type=sign_type,
                sign_by=name if sign_by else "",
                date=date,
                reason=reason,
                no_design=no_design
            )

            if base64_output:
                return html_signature

            # Placeholder: Upload logic
            user = User()
            img = user.upload_file(html_signature if sign_type == 'full' else f"data:image/png;base64,{image_base64}", "signature")
            return {"hash": hash_key, "image": img}
        except Exception as e:
            _logger.error(f"Error uploading signature: {str(e)}")
            raise e

    def get_new_sign(self,get_dsign):
        """
        Generates a new signature based on the provided details.

        :param get_dsign: Dictionary containing details of the signature to generate.
        :return: A dictionary containing the success status and base64 encoded signature image.
        """
        try:
            # Extract details from `get_dsign`
            date = get_dsign.date
            reason = get_dsign.reason
            sign_by = get_dsign.sign_by
            signature_font = get_dsign.signature_font
            full_name = get_dsign.full_name
            signature = get_dsign.signature
            no_design = get_dsign.no_design
            sig_type = get_dsign.type

            # Format the date
            if date:
                date = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S") + " (UTC)"

            base64_signature = ""

            # Handle the "choose" signature type
            if sig_type == "choose":
                base64_signature = self.upload_signature(
                    name=full_name,
                    font_path=f"{server_path}/dms_editor/static/src/fonts/sign{signature_font}.ttf" if signature_font != 'roboto' else f"{server_path}/dms_editor/static/src/fonts/{signature_font}.ttf",
                    sign_type="full",
                    sign_by=sign_by,
                    date=date,
                    reason=reason,
                    no_design=no_design,
                    base64_output=True,
                )

            # Handle the "draw" or "upload" signature type
            elif sig_type in ["draw", "upload"]:
                hash_key = self.file_hash(signature, "file")  # Simulate hash_key
                base64_signature = self.generate_html_signature_base64(
                    image_data=signature,
                    hash_key="",
                    sign_type="full",
                    sign_by="",
                    date="",
                    reason="",
                    no_design=""
                )

            return {"success": True, "data": base64_signature}

        except Exception as e:
            _logger.error(f"Error generating new signature: {str(e)}")
            return {
                "success": False,
                "message": "Error occurred! Please try again.",
                "e": str(e)
            }

    def remove_old_signature(self,url, sign_type=""):
        """Remove old signature from storage."""
        db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
        if url:
            if sign_type == 'choose':
                gcs.delete_file(f"{db_name}/signature/{url.split('/').pop()}")
            else:
                gcs.delete_file(f"{db_name}/user/{url.split('/').pop()}")
            return True
        return False

    def file_hash(self, filename, input_type):
        """
        Generate a SHA-512 hash for a file or string.

        :param filename: str - The file path (for file hashing) or the string (for base64 hashing).
        :param input_type: str - The type of input ('base64' or 'file').
        :return: str - The generated hash or an empty string in case of an error.
        """
        try:
            # For base64 input type, calculate hash directly from the string
            if input_type == "base64":
                hash_object = hashlib.sha512()
                hash_object.update(filename.encode('utf-8'))
                return hash_object.hexdigest()
            
            # For file input type, calculate hash from the file content
            elif input_type == "file":
                hash_object = hashlib.sha512()
                with open(filename, 'rb') as file:
                    for chunk in iter(lambda: file.read(4096), b""):
                        hash_object.update(chunk)
                return hash_object.hexdigest()
        
        except Exception as e:
            _logger.error(f"Error generating file hash: {str(e)}")
            return ""
