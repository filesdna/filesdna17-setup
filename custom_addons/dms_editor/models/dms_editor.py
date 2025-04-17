from odoo import models, fields, api
import io
import base64
import random
import string
from datetime import datetime
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image
from odoo.addons.dms_editor.services.blockchain import BlockchainService

class DmsEditor(models.Model):
    _inherit = 'dms.file'

    ref_number = fields.Char(string='Reference Number', required=False)
    json_version = fields.Integer(string='JSON Version', required=False)
    document_json = fields.Text(string='Document JSON', required=False)
    append_json = fields.Text(string='Append JSON', required=False)
    barcode_url = fields.Char(string='Barcode URL', compute='generate_alphanumeric_barcode', store=True, readonly=True)
    barcode = fields.Char(string='Barcode', compute='generate_alphanumeric', store=True, readonly=True)
    password = fields.Char(string='Password', required=False)
    qr_code = fields.Text(string='QR Code',required=False)
    bc_document = fields.Text(string='Blockchain Document',required=False)
    bc_signature_hash = fields.Char(string='Blockchain Signature Hash', required=False)    

    def generate_alphanumeric(self):
        """
        Generates an alphanumeric string in the format:
        4 random digits + 4 random letters/numbers + 2 random digits.

        Returns:
            str: The generated alphanumeric string.
        """
        # Generate 4 random digits
        digits_part1 = ''.join(random.choices(string.digits, k=4))
        
        # Generate 4 random alphanumeric characters
        alpha_numeric = "abcdefghijklmnopqrstuvwxyz123456789"
        alphanumeric_part = ''.join(random.choices(alpha_numeric, k=4))
        
        # Generate 2 random digits
        digits_part2 = ''.join(random.choices(string.digits, k=2))
        
        # Combine all parts
        alphanumeric_string = f"{digits_part1}{alphanumeric_part}{digits_part2}"
        self.barcode = alphanumeric_string
        return alphanumeric_string

    @api.depends('attachment_ids')
    def generate_alphanumeric_barcode(self):
        """
        Generates a barcode image with specific dimensions and returns it as a base64 encoded string.

        Returns:
            str: Base64 encoded string of the generated barcode image.
        """
        # Generate barcode with Code128 format (supports alphanumeric)
        data = self.generate_alphanumeric()
        barcode = Code128(data, writer=ImageWriter())

        # Save the barcode image to an in-memory file (BytesIO) with high DPI for scaling
        barcode_buffer = io.BytesIO()
        barcode.write(barcode_buffer, options={"dpi": 300})  # High DPI for resizing later

        # Resize the image to match the provided dimensions (example: 288x142 pixels)
        target_width = 288
        target_height = 142
        barcode_buffer.seek(0)
        image = Image.open(barcode_buffer)

        # Resize the barcode while maintaining aspect ratio
        image = image.resize((target_width, target_height), Image.LANCZOS)

        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        base64_barcode = f"data:image/png;base64,{base64_image}"

        self.barcode_url = base64_barcode

    def create_document_blockchain(self):
        """
        Creates a blockchain record for the document using the BlockchainService.
        Calls the `add_document_in_blockchain` method.

        Returns:
            dict: Response from the blockchain service.
        """
        bc = BlockchainService()
        for record in self:
            blockchain_data = {
                'user_id': record.create_uid.blockchain_uid,
                'hash': record.sha512_hash,  # Assuming `sha512_hash` is a field containing the document's hash
            }
            blockchain_response = bc.add_document_in_blockchain(blockchain_data)

            # Update the document record with blockchain data
            if blockchain_response:
                record.write({
                    'bc_document': blockchain_response.get('bc_document', ''),
                })

        return blockchain_response
