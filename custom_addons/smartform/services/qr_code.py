import qrcode
from PIL import Image

def generate_branded_qr(text, logo_path, output_path, ratio=2, error_correction=qrcode.constants.ERROR_CORRECT_H):
    """
    Generate a branded QR code with a logo in the center.

    :param text: The text to encode in the QR code.
    :param logo_path: The path to the logo image.
    :param output_path: The path where the generated QR code will be saved.
    :param ratio: The size ratio between the QR code and the logo.
    :param error_correction: The error correction level for the QR code.
    """
    try:
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
        return output_path

    except Exception as e:
        raise ValueError(f"Error generating branded QR code: {str(e)}")
