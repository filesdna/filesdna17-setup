import qrcode
from PIL import Image
import random
import base64
import os
from odoo.http import request
from odoo.tools import config

server_path = config['server_path']

def generate_branded_qr(hash=None):
    """
    Generate a branded QR code with a logo in the center.
    """
    try:
        ratio=2
        link = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not hash:
            hash = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=50))
        text = f"{link}/qrdetails/{hash}"
        error_correction = qrcode.constants.ERROR_CORRECT_H
        output_path = os.path.join('/tmp', f"{hash}_qr.png")
        logo_path = f'{server_path}/dms_editor/static/src/images/logo/logo.png'
        if not os.path.exists('/tmp'):
            raise ValueError("The temporary directory '/tmp' does not exist.")
        # Generate the QR code
        qr = qrcode.QRCode(
            error_correction=error_correction,
            box_size=10,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Create the QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        # Open the logo image
        logo = Image.open(logo_path)

        # Calculate the size and position of the logo
        qr_width, qr_height = qr_img.size
        logo_size = (qr_width // ratio, qr_height // ratio)
        logo.thumbnail(logo_size, Image.LANCZOS)
        logo_pos = ((qr_width - logo_size[0]) // 2, (qr_height - logo_size[1]) // 2)

        # Overlay the logo on the QR code
        qr_img.paste(logo, logo_pos, mask=logo if logo.mode == "RGBA" else None)

        # Save the QR code image with the logo
        qr_img.save(output_path)

        with open(output_path, 'rb') as qr_file:
            qr_code = f"data:image/png;base64,{base64.b64encode(qr_file.read()).decode()}"

        os.remove(output_path)
        return qr_code

    except Exception as e:
        raise ValueError(f"Error generating branded QR code: {str(e)}")
