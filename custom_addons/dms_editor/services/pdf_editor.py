import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from odoo.http import request
import logging
from odoo.tools import config
import base64
from cairosvg import svg2png
from bidi.algorithm import get_display  # For proper Arabic/RTL support
import tempfile
from arabic_reshaper import reshape  # To reshape Arabic text
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
import re

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class PdfEditorService:
    def modify_pdf_content(self, json_data, document_id):
        """
        Modify the PDF content based on provided JSON data.

        :param json_data: list - The JSON data containing modifications.
        :param document_id: int - The ID of the document.
        :return: str - The modified PDF file name or False on failure.
        """
        try:
            get_file = request.env['dms.file'].sudo().search([('id', '=', document_id)])
            if not get_file:
                _logger.error("File not found.")
                return False

            try:
                # Define path for JSON retrieval based on the environment setup
                _temp = f"{server_path}/dms_editor/static/src/temp"
                local_pdf_path = os.path.join(_temp, get_file.attachment_id.store_fname.split('/')[1])
                if os.path.exists(local_pdf_path):
                    os.remove(local_pdf_path)
                db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]    
                destination_path = f"{db_name}/{get_file.attachment_id.store_fname}"
                gcs_service = LocalStorageService()
                gcs_service.download_file(destination_path, local_pdf_path, encryption_key=None)
                
            except Exception as e:
                _logger.error(f"Error retrieving pdf file: {str(e)}")
                return False

            doc = fitz.open(local_pdf_path)

            for append in json_data:
                if append['type'] == 'setting':
                    continue

                page = doc[append['page'] - 1]
                width, height = page.rect.width, page.rect.height
                zoom = width / 900
                
                if append['type'] in ['textbox', 'date', 'email', 'textbox1', 'time', 'date1', 'refnumber']:
                    self._draw_textbox(page, append, zoom, width, height)

                if append['type'] in ['sign', 'initial', 'icon', 'qr', 'barcode']:
                    self._draw_image(page, append, zoom, width, height)

                if append['type'] in ['checkbox', 'radio']:
                    self._draw_checkbox_or_radio(page, append, zoom, width, height)

                if append['type'] == 'highlight':
                    self._draw_highlight(page, append, zoom, width, height)

                if append['type'] == 'dropdown':
                    self._draw_dropdown(page, append, zoom, width, height)
                
                if append['type'] == 'watermark':
                    self._draw_watermark(page, append, zoom, width, height)
                    
                if append['type'] == 'image':
                    self._draw_embedded_image(page, append, zoom, width, height)

            modified_pdf_name = f"{get_file.name}"
            modified_pdf_path = os.path.join(f'{server_path}/dms_editor/static/src/assets',"pdf", modified_pdf_name)
            doc.save(modified_pdf_path)
            _logger.info(f"Modified PDF saved at {modified_pdf_path}")
            return modified_pdf_name

        except Exception as e:
            _logger.error(f"Error modifying PDF content: {str(e)}")
            return False

    def _draw_textbox(self, page, append, zoom, width, height):
        """
        Draw a multi-line text box on the page, adjusting the rectangle size dynamically if needed.

        :param page: fitz.Page - The page to draw on.
        :param append: dict - The data for the text box.
        :param zoom: float - The zoom factor for scaling.
        :param width: float - The page width.
        :param height: float - The page height.
        """
        font_dir = f'{server_path}/dms_editor/static/src/fonts/pdfFont'
        font_family = "Dubai" if append["type"] == "refnumber" else append["font"]["family"]
        font_path = os.path.join(font_dir, f"{font_family}-Regular.ttf")

        try:
            # Load custom font or fallback
            if not os.path.exists(font_path):
                _logger.warning(f"Font file not found: {font_path}. Falling back to Times-Roman.")
                font_family = "Times-Roman"
                font_path = None

            # Extract text and settings
            text = append["data"]
            text_color = self._hex_to_rgb(append['font']['color'])
            alignment_str = append['font'].get('align', 'left').lower()  # Default to "left"

            # Map alignment to PyMuPDF constants
            alignment_map = {
                "left": fitz.TEXT_ALIGN_LEFT,
                "center": fitz.TEXT_ALIGN_CENTER,
                "right": fitz.TEXT_ALIGN_RIGHT,
            }
            alignment = alignment_map.get(alignment_str, fitz.TEXT_ALIGN_LEFT)
            
            # Handle Arabic/RTL text
            if self._contains_arabic(text):
                text = get_display(reshape(text))

            # Define rectangle for the text box
            x_start = (append["position"]["x"]) * zoom 
            y_start = (append["position"]["y"] + 4) * zoom
            max_width = (append["size"]["width"] + 1) * zoom
            max_height = (append["size"]["height"] + 1) * zoom
            rect = fitz.Rect(x_start, y_start, x_start + max_width, y_start + max_height)

            # Register custom font if specified
            if font_path:
                page.insert_font(fontname="F0", fontfile=font_path)
                font_name = "F0"
            else:
                font_name = "Times-Roman"

            # Dynamically adjust font size and expand the rectangle if needed
            font_size = (append.get('font', {}).get('size', 12) - 2) * zoom
            text_lines = text.split("\n")  # Split text into lines

            # Estimate height required for text
            text_height = font_size * len(text_lines) * 1.2  # 1.2 is a line spacing factor

            if text_height > max_height:  # Expand the rectangle to fit text
                max_height = text_height
                rect = fitz.Rect(x_start, y_start, x_start + max_width, y_start + max_height)

            # Try inserting text
            rc = page.insert_textbox(rect, text, fontsize=font_size, fontname=font_name, color=text_color, align=alignment)

            # If text still doesn't fit, increase rectangle height dynamically
            while rc < 0 and font_size > 1:
                max_height += font_size * 1.2  # Increase height
                rect = fitz.Rect(x_start, y_start, x_start + max_width, y_start + max_height)
                rc = page.insert_textbox(rect, text, fontsize=font_size, fontname=font_name, color=text_color, align=alignment)

            if rc < 0:
                _logger.warning(f"Text could not fit within the rectangle even after expanding.")

        except Exception as e:
            _logger.error(f"Error drawing text box: {str(e)}")


    def _draw_image(self, page, append, zoom, width, height):
        temp_file = None
        try:
            # Extract image data
            image_data = append.get('data')
            if not image_data:
                _logger.warning("No image data provided for drawing.")
                return
            # Decode Base64 image
            png_data = None
            if image_data.startswith("data:image/png;base64,"):
                try:
                    png_data = base64.b64decode(image_data.split(",")[1])
                except Exception as decode_error:
                    _logger.error(f"Error decoding Base64 image: {str(decode_error)}")
                    return
            elif '<svg' in image_data:  # Handle SVG data
                try:
                    png_data = svg2png(
                        bytestring=image_data.encode('utf-8'),
                        output_width=append['size']['width'],
                        output_height=append['size']['height']
                    )
                except Exception as svg_error:
                    _logger.error(f"Error converting SVG to PNG: {str(svg_error)}")
                    return
            else:
                _logger.error("Unsupported image format or data.")
                return

            # Verify PNG data is not empty
            if not png_data:
                _logger.error("Failed to process image data.")
                return

            # Save PNG to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.write(png_data)
            temp_file.close()

            # Create Pixmap from PNG file
            pixmap = None
            try:
                pixmap = fitz.Pixmap(temp_file.name)
            except Exception as pixmap_error:
                _logger.error(f"Error creating Pixmap from image data: {str(pixmap_error)}")
                return
            ratio = 0
            # Determine image height based on type
            if append['type'] == 'sign':
                ratio_x = 0
                ratio_y = 0
            elif append['type'] == 'initial':
                ratio_x = 0
                ratio_y = 0
            else:
                img_height = 0
                if append['type'] == 'barcode':
                    ratio_x = 0
                    ratio_y = 0
                    img_height = 0
                elif append['type'] == 'qr':
                    ratio_x = 0
                    ratio_y = 5

            # Define the image rectangle
            # Correct calculation for fitz.Rect
            x0 = (append['position']['x'] - ratio_x) * zoom 
            y0 = (append['position']['y'] * zoom)
            x1 = x0 + ((append['size']['width'] + ratio_x) * zoom) 
            y1 = y0 + (append['size']['height'] * zoom) + ratio_y

            # Validate coordinates
            img_rect = fitz.Rect(x0, y0, x1, y1)
            _logger.info(f"Position x: {append['position']['x']}, y: {append['position']['y']}")
            _logger.info(f"Size width: {append['size']['width']}, height: {append['size']['height']}")
            _logger.info(f"Page height: {height}, width: {width}")
            _logger.info(f"Zoom: {zoom}")
            _logger.info(f"Calculated img_rect: {img_rect}")
            # Insert the image into the page
            page.insert_image(img_rect, pixmap=pixmap)
            _logger.info(f"Image successfully drawn at position {append['position']}.")

        except Exception as e:
            _logger.error(f"Error drawing image: {str(e)}")
        finally:
            # Delete the temporary file
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)
                _logger.info(f"Temporary file {temp_file.name} deleted.")


    def _draw_checkbox_or_radio(self, page, append, zoom, width, height):
        local_path = f'{server_path}/dms_editor/static/src/fonts'
        img_name = "checkedc.png" if append['type'] == 'checkbox' and append['checked'] else \
                   "checkedr.png" if append['type'] == 'radio' and append['checked'] else \
                   "uncheckedc.png" if append['type'] == 'checkbox' else \
                   "uncheckedr.png"
        img_path = os.path.join(local_path, img_name)

        x0 = append['position']['x'] * zoom
        y0 = (append['position']['y']) * zoom
        x1 = x0 + (30 * zoom)
        y1 = y0 + (30 * zoom)

        img_rect = fitz.Rect(x0, y0, x1, y1)
        page.insert_image(img_rect, filename=img_path)

    def _draw_highlight(self, page, append, zoom, width, height):
        try:

            x0 = append['position']['x'] * zoom
            y0 = append['position']['y'] * zoom
            x1 = x0 + (append['size']['width'] * zoom)
            y1 = y0 + (append['size']['height'] * zoom)

            rect = fitz.Rect(x0, y0, x1, y1)
            # Yellow with 50% opacity
            color = (1.0, 1.0, 0.0)  # RGB for yellow
            page.draw_rect(rect, color=color, fill=color, fill_opacity=0.4)
        except Exception as e:
            _logger.error(f"Error drawing highlight: {str(e)}")

    def _draw_dropdown(self, page, append, zoom, width, height):
        font_dir = f'{server_path}/dms_editor/static/src/fonts/pdfFont'
        font_family = "Dubai" if append["type"] == "refnumber" else append["font"]["family"]
        font_path = os.path.join(font_dir, f"{font_family}-Regular.ttf")
        font_size = append.get('font', {}).get('size', 12) * zoom
        try:
            # Load custom font or fallback
            if not os.path.exists(font_path):
                _logger.warning(f"Font file not found: {font_path}. Falling back to Times-Roman.")
                font_family = "Times-Roman"
                font_path = None
            text = append["data"]
            text_color = self._hex_to_rgb(append['font']['color'])
            
            # Handle Arabic/RTL text
            if self._contains_arabic(text):
                text = get_display(reshape(text))

            # Define rectangle for the text box
            x0 = append['position']['x'] * zoom
            y0 = append['position']['y'] * zoom
            x1 = x0 + font_size + 12
            y1 = y0 + font_size + 12

            rect = fitz.Rect(x0, y0, x1, y1)

            # Register custom font if specified
            if font_path:
                page.insert_font(fontname="F0", fontfile=font_path)
                font_name = "F0"
            else:
                font_name = "Times-Roman"

            # Dynamically adjust font size to fit text in the rectangle
            
            rc = page.insert_textbox(rect, text, fontsize=font_size, fontname=font_name, color=text_color)
            while rc < 0 and font_size > 1:  # Adjust font size if the text doesn't fit
                font_size -= 1
                rc = page.insert_textbox(rect, text, fontsize=font_size, fontname=font_name, color=text_color)

            if rc < 0:
                _logger.warning(f"Text could not fit within the rectangle even at the smallest font size.")

        except Exception as e:
            _logger.error(f"Error drawing dropdown text: {str(e)}")

    def _draw_watermark(self, page, append, zoom, width, height):
        """
        Draw a watermark on a PDF page.

        :param page: fitz.Page - The page to draw the watermark on.
        :param append: dict - Data for the watermark.
        :param zoom: float - Scaling factor for positions and sizes.
        :param width: float - Page width.
        :param height: float - Page height.
        """
        try:
            # Extract font color
            color = append["font"]["color"]
            font_color = self._rgba_to_rgb(color) if "rgba" in color else self._hex_to_rgb(color)

            # Adjust position based on angle
            add_x = 100 if append.get("angle") and append["angle"] not in [0, -90] else 300 if append.get("angle") == -90 else 0
            add_y = 200 if append.get("angle") and append["angle"] != 0 else 0

            # Compute the final position
            x = (append["position"]["x"] + add_x) * zoom
            y = ((append["position"]["y"] + add_y - 10) + append["font"]["size"]) * zoom  # -5 adjusts alignment

            # Embed font (custom or fallback to default)
            font_dir = f'{server_path}/dms_editor/static/src/fonts/pdfFont'
            font_path = os.path.join(font_dir, f"{append['font']['family']}-Regular.ttf")
            if os.path.exists(font_path):
                page.insert_font(fontname="F0", fontfile=font_path)
                font_name = "F0"
            else:
                _logger.warning(f"Font file not found: {font_path}. Falling back to Times-Roman.")
                font_name = "Times-Roman"

            text = append['data']
            # Handle Arabic/RTL text
            if self._contains_arabic(text):
                text = get_display(reshape(text))

            _logger.info(f"append:{append['angle']}")
            _logger.info(f"opacity:{append.get('opacity')}")
            fixpoint = fitz.Point(x, y)

            if append["angle"] == 0:
                angle = fitz.Matrix(0)
            elif append['angle'] == -90:
                angle = fitz.Matrix(90)
            else:
                angle = fitz.Matrix(45)
            
            # Draw watermark text
            page.insert_text(
                point=fixpoint,
                text=text,
                fontsize=append["font"]["size"] * zoom,
                fontname=font_name,  # Use the registered font alias
                color=font_color,
                render_mode=0,  # Text is rendered as stroke and fill
                morph=(fixpoint, angle),
                fill_opacity=0.1  # Default opacity is 0.5

            )

        except Exception as err:
            _logger.error(f"Error drawing watermark: {str(err)}")


    def _draw_embedded_image(self, page, append, zoom, width, height):
        """
        Embed and draw an image (JPEG or PNG) on the page.

        :param page: fitz.Page - The page to draw on.
        :param append: dict - The data for the image to be embedded.
        :param zoom: float - The zoom factor for scaling.
        :param width: float - The page width.
        :param height: float - The page height.
        """
        try:
            # Extract image data
            image_data = append.get('data')
            if not image_data:
                _logger.warning("No image data provided for drawing.")
                return
            # Decode Base64 image
            png_data = None
            if image_data.startswith("data:image/png;base64,"):
                try:
                    png_data = base64.b64decode(image_data.split(",")[1])
                except Exception as decode_error:
                    _logger.error(f"Error decoding Base64 image: {str(decode_error)}")
                    return
            elif '<svg' in image_data:  # Handle SVG data
                try:
                    png_data = svg2png(
                        bytestring=image_data.encode('utf-8'),
                        output_width=append['size']['width'],
                        output_height=append['size']['height']
                    )
                except Exception as svg_error:
                    _logger.error(f"Error converting SVG to PNG: {str(svg_error)}")
                    return
            else:
                _logger.error("Unsupported image format or data.")
                return

            # Verify PNG data is not empty
            if not png_data:
                _logger.error("Failed to process image data.")
                return

            # Save PNG to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.write(png_data)
            temp_file.close()

            # Create Pixmap from PNG file
            pixmap = None
            try:
                pixmap = fitz.Pixmap(temp_file.name)
            except Exception as pixmap_error:
                _logger.error(f"Error creating Pixmap from image data: {str(pixmap_error)}")
                return
            # Determine the image dimensions
            img_height = append["size"]["height"]
            img_rect = fitz.Rect(
                append["position"]["x"] * zoom,
                (append["position"]["y"]) * zoom,
                (append["position"]["x"] + append["size"]["width"]) * zoom,
                (append["position"]["y"] + append["size"]["height"]) * zoom
            )

            # Draw the image on the page
            page.insert_image(img_rect, pixmap=pixmap)

        except Exception as e:
            _logger.error(f"Error embedding image on page {page.number}: {str(e)}")
            raise ValueError(f"Image embedding failed for {append.get('data')}")
        finally:
            # Delete the temporary file
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)
                _logger.info(f"Temporary file {temp_file.name} deleted.")

    def _draw_justified_line(self, page, line, x_start, y_position, max_width, font_size, font, color, is_arabic):
        """
        Draw a justified line of text.

        :param page: fitz.Page - The page to draw on.
        :param line: list - The words in the line.
        :param x_start: float - Starting x-coordinate.
        :param y_position: float - Starting y-coordinate.
        :param max_width: float - Maximum width for the line.
        :param font_size: float - Font size for the text.
        :param font: fitz.Font - Font object to use.
        :param color: tuple - RGB color values.
        :param is_arabic: bool - Whether the text contains Arabic characters.
        """
        total_space_width = max_width - sum(font.text_length(word, font_size) for word in line)
        num_spaces = len(line) - 1 + (1 if is_arabic else 0)  # Arabic may require an extra space
        extra_space = total_space_width / num_spaces if num_spaces > 0 else 0

        x_position = x_start
        for index, word in enumerate(line):
            # Draw the word
            page.insert_text(
                point=(x_position, y_position),
                text=word,
                fontsize=font_size,
                fontfile=font,
                color=color
            )

            # Update x_position for the next word
            word_width = font.text_length(word, font_size)
            x_position += word_width + extra_space

            # For Arabic, skip the extra space for the first word
            if is_arabic and index == 0:
                x_position -= extra_space

    def _get_aligned_position(self, alignment, line_width, max_width, x_start):
        """
        Get the starting x-position for a line of text based on alignment.

        :param alignment: str - Text alignment ("left", "center", "right").
        :param line_width: float - The width of the line.
        :param max_width: float - The maximum width for the line.
        :param x_start: float - The starting x-coordinate.
        :return: float - The adjusted x-coordinate for the alignment.
        """
        if alignment == "center":
            return x_start + (max_width - line_width) / 2
        elif alignment == "right":
            return x_start + (max_width - line_width)
        return x_start

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def _contains_arabic(self, text):
        return any('\u0600' <= char <= '\u06FF' for char in text)

    def _rgba_to_rgb(self, rgba_color):
        """
        Convert an RGBA or RGB color string to an RGB tuple.

        :param rgba_color: str - The RGBA or RGB color string (e.g., "rgba(255, 0, 0, 0.5)" or "rgb(255, 0, 0)").
        :return: tuple - RGB values (r, g, b) normalized to [0, 1].
        """
        import re
        # Match both rgba and rgb formats
        rgba_match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+),?\s*([\d.]+)?\)", rgba_color)
        if rgba_match:
            r, g, b = map(int, rgba_match.groups()[:3])  # Extract R, G, B
            return r / 255, g / 255, b / 255
        raise ValueError(f"Invalid RGBA or RGB color format: {rgba_color}")