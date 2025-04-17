import pdfkit
import os
import zipfile
from datetime import datetime
import json
from odoo.http import request
from odoo.addons.smartform.services.google_storage import LocalStorageService
from odoo.tools import config
from typing import List, Dict, Any
import requests
import logging

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class PDFService:

    def __init__(self, template_dir=f'{server_path}/smartform/static/src/assets/forms/templates'):
        self.template_dir = template_dir

    def get_form_data(self, form_hash):
        """Fetch and decrypt form data from Google Cloud Storage."""
        try:
            # Fetch the form
            db_name = request._cr.dbname
            form = request.env['smart.form'].sudo().search([('hash', '=', form_hash)], limit=1)
            if not form:
                raise ValueError(f"No form found with hash {form_hash}")

            user = request.env['res.users'].sudo().browse(form.user_id.id)
            if not user:
                raise ValueError(f"No user found for form {form_hash}")

            temp_path = str(f'{server_path}/smartform/static/src/assets/forms/{form.form_data}')

            gcs_service = LocalStorageService()
            _logger.info(f"user::::{user}")
            encryption_key = user.company_id.encription_key
            _logger.info(f"encryption_key::::{encryption_key}")
            # Download the form data from Google Cloud Storage
            gcs_service.download_file(
                f"{db_name}/smartform/forms/{form.form_data}",
                temp_path,
                encryption_key
            )

            with open(temp_path, 'r') as f:
                form_data = json.load(f)

            os.unlink(temp_path)
            return form_data

        except Exception as e:
            raise ValueError(f"Error fetching form data: {str(e)}")


    def generate_pdfs_and_zip(self, form_data, submissions):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        temp_dir = os.path.join(self.template_dir, timestamp)
        os.makedirs(temp_dir, exist_ok=True)

        # Use valid wkhtmltopdf options
        options = {
            'page-size': 'A4', 
            'orientation': 'Portrait',
            'margin-top': '30mm',
            'margin-bottom': '30mm',
            'margin-left': '30mm',
            'margin-right': '30mm',
            'encoding': "UTF-8",
        }
        _logger.info(f"Form Data1: {form_data}")
        _logger.info(f"Form Data2: {json.dumps(form_data, indent=2)}")
        files = []  # Store PDF paths for zipping

        # Iterate over each submission and map values to the form
        for submission in submissions:
            value_data = json.loads(submission.data)  # Parse submission data

            # Update form values with submission data
            self.map_submission_to_form(value_data, form_data['form'])

            # Generate HTML content for the updated form
            html_content = self.generate_html_content(form_data['form'], form_data['setting'])
            _logger.info(f"Generated HTML Content: {html_content}")

            # Create a PDF file for the submission
            pdf_path = os.path.join(temp_dir, f"{submission.create_date}.pdf")
            pdfkit.from_string(html_content, pdf_path, options=options)
            files.append(pdf_path)  # Store the file path

        # Create a ZIP archive containing all PDFs
        zip_path = os.path.join(self.template_dir, f"{timestamp}.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for pdf in files:
                zipf.write(pdf, os.path.basename(pdf))

        # Clean up temporary files
        for pdf in files:
            os.remove(pdf)
        os.rmdir(temp_dir)

        return zip_path  # Return the path to the ZIP archive

    def map_submission_to_form(self,submitted_values, form):
        """Map submitted values to form elements even when 'id' is missing."""
        mapped_form = []

        # Create a dictionary of submitted values indexed by 'id' (if available)
        submitted_dict = {
            value.get('id'): value.get('value') for value in submitted_values if 'id' in value
        }

        for element in form:
            element_id = element.get('id')

            # Log a warning if 'id' is missing, but continue processing
            if element_id is None:
                _logger.warning(f"Form item missing 'id': {element}")

            # Assign the submitted value if the element has an 'id'
            if element_id in submitted_dict:
                element['value'] = submitted_dict[element_id]
            else:
                # Handle cases where 'id' is missing or no matching value exists
                element['value'] = element.get('value', None)

            # Add the processed element to the mapped form
            mapped_form.append(element)

        return mapped_form


    def format_date(self, date_str, date_format='DD/MM/YYYY'):
        """Format date strings to the required format."""
        try:
            # Handle standard ISO format
            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            # If the format doesn't match, use manual parsing
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')

        # Format to the desired output
        formatted_date = parsed_date.strftime(
            date_format.replace('DD', '%d').replace('MM', '%m').replace('YYYY', '%Y')
        )
        return formatted_date

    def render_value(self, el: Dict[str, Any]) -> str:
        """Replicate the render logic from Sails.js."""
        el_type = el.get('type')
        value = el.get('value', '')

        if not value and el_type != 'image':
            return ''

        if el_type == 'appointment':
            return f"{self.format_date(value[0], el.get('dateFormat', 'DD/MM/YYYY')) if value[0] else ''} {value[1] or ''}"

        if el_type == 'datePicker':
            date_part = self.format_date(value[0], el.get('format', 'DD/MM/YYYY')) if value and value[0] else ''
            time_part = datetime.strptime(value[1], '%H:%M').strftime(el.get('timeFormat', 'HH:mm')) if value and len(value) > 1 and value[1] else ''
            return f"{date_part} {time_part}"

        if el_type == 'time':
            return ' - '.join(
                [datetime.strptime(v, '%H:%M').strftime(el.get('timeFormat', 'HH:mm')) for v in value]
            ) if isinstance(value, list) else datetime.strptime(value, '%H:%M').strftime(el.get('timeFormat', 'HH:mm'))

        if el_type in ['fullname', 'phone']:
            # Handle None values and ensure all elements are strings
            return ' '.join([str(v) for v in value if v is not None])

        if el_type == 'address':
            return ', '.join([str(v) for v in value if v])

        if el_type == 'signature' and self.is_valid_image_url(el.get('signature')):
            return f"<img src='{value[0]}' width='{value[1]}' alt='filesdna-sign' />"

        if el_type == 'imageSelect' and self.is_valid_image_url(el.get('imageSelect')):
            return f"<img src='{value}' alt='filesdna-image' width='100' />"

        if el_type == 'image' and self.is_valid_image_url(el.get('image')):
            return f"""
                <div style='text-align: {el.get('align', 'center')}'>
                    <img src='{el['image']}' width='{el['width']}' 
                         height='{el.get('height', 'auto') if not el.get('lock') else 'auto'}' />
                </div>
            """

        if el_type == 'fileUpload':
            return ''.join([
                f"<span class='glyphicon glyphicon-paperclip'></span>"
                f"<a href='{v.get('url', '')}' target='_blank' rel='noreferrer'>{v.get('name', '')}</a><br />"
                for v in value if v.get('url') and v.get('name')
            ])

        if el_type == 'inputTable':
            result = "<table class='submission-table'><tr><td class='empty' /></tr>"
            result += ''.join([f"<td class='title'>{col}</td>" for col in value['cols'].split('\n')])
            result += "</tr>"

            for row in value['rows'].split('\n'):
                result += f"<tr><td class='title'>{row}</td>"
                result += ''.join([
                    f"<td><input type='{'radio' if value['inputType'] == 1 else 'checkbox'}' "
                    f"{'checked' if (value['value'][row] if value['inputType'] == 1 else col) in value['value'][row] else ''} /></td>"
                    for col in value['cols'].split('\n')
                ])
                result += "</tr>"

            result += "</table>"
            return result

        return str(value)


    
    def generate_html_content(self, form: List[Dict[str, Any]], setting: Dict[str, Any]) -> str:
        """Generate HTML content dynamically from form data."""

        form_image = setting.get('formImage', '')
        background_style = (
            f"background-image: url({form_image}); background-size: cover;"
            if self.is_valid_image_url(form_image) else ""
        )
        # Find the logo element, if available
        logo = next((el for el in form if el.get('type') == 'logo'), None)

        # Start building the HTML content
        content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>PDF Export</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
            <style>
                *{{ -webkit-print-color-adjust: exact; }}
                .container{{ padding: 50px; min-height: 100vh; {background_style} }}
                .row > div{{ padding: 20px; }}
                .rtl, .rtl *{{ direction: rtl; unicode-bidi: bidi-override; }}
                td{{ padding: 10px; border: 1px solid #d9d9d9; text-align: center; }}
                td.empty{{ border: none; }}
                td.title{{ background: rgb(13, 184, 173); color: white; }}
                div.flex{{ display: flex; }}
                div.flex > *{{ margin-right: 5px !important; }}
                div.center{{ text-align: center; }}
            </style>
        </head>
        <body>
        <div class="container">
            <div class="row">
        """

        # Add the logo if available and valid
        logo = next((el for el in form if el['type'] == 'logo'), None)
        if logo and self.is_valid_image_url(logo.get('logoImage')):
            content += f"""
                <div style='text-align: {logo.get('align', 'center')}; 
                            width: {setting.get('formWidth', 100)}px; padding: 20px 0;'>
                    <img src='{logo['logoImage']}' width='{logo['size']}px' />
                </div>
            """

        # Sort and iterate through form elements
        sorted_form = sorted(form, key=lambda el: (el.get('page', 0), el.get('order', 0)))
        for el in sorted_form:
            direction_class = el.get('textDirection', 'LTR').lower()
            if el.get('type') == 'heading':
                content += self.generate_heading(el)

            elif el.get('type') == 'divider':
                content += self.generate_divider(el)

            else:
                content += f"""
                <div class="col-xs-{6 if el.get('shrink') else 12} {direction_class}">
                    <label>{el.get('label', '') or ''}</label>
                    <div>{self.render_value(el)}</div>
                </div>
                """

        # Close the HTML tags
        content += """
            </div>
        </div>
        </body>
        </html>
        """

        return content

    def show_color(self, color: Dict[str, str]) -> str:
        """Convert RGB color values to rgba format."""
        return f"rgba({color.get('r', 0)}, {color.get('g', 0)}, {color.get('b', 0)}, {color.get('a', 1)})"

    def generate_heading(self, el: Dict[str, Any]) -> str:
        """Generate HTML for a heading element."""
        if not el.get('img'):
            return f"""
            <div class="col-xs-12" style="font-size: {el.get('size', 20)}px; text-align: {el.get('align', 'left')}">
                {el.get('text', '')}<br/>
                <small><small>{el.get('subText', '')}</small></small>
            </div>
            """
        elif el.get('img') and self.is_valid_image_url(el.get('img')):
            return f"""
            <div class="{ 'col-xs-12 flex' if el.get('imgAlign') != 'top' else 'col-xs-12 center' }">
                { f"<img src='{el['img']}' width='{el.get('imgWidth', 140)}px' />" if el.get('imgAlign') != 'right' else '' }
                <div style="display: table">
                    <div style="font-size: {el.get('size', 20)}px; text-align: {el.get('align', 'left')}; display: table-cell; vertical-align: {el.get('txtAlign', 'middle')}">
                        {el.get('text', '')}<br/>
                        <small><small>{el.get('subText', '')}</small></small>
                    </div>
                </div>
                { f"<img src='{el['img']}' width='{el.get('imgWidth', 140)}px' />" if el.get('imgAlign') == 'right' else '' }
            </div>
            """

    def generate_divider(self, el: Dict[str, Any]) -> str:
        """Generate HTML for a divider element."""
        return f"""
        <div class='col-xs-12'>
            <div style="border-top: {el.get('height', 1)}px {el.get('lineStyle', 'solid')} {self.show_color(el.get('lineColor', {}))}; 
                        margin: {el.get('spaceAbove', 10)}px {el.get('horizonSpace', 10)}px {el.get('spaceBelow', 10)}px;">
            </div>
        </div>
        """

    # Check if an image URL is valid and accessible
    def is_valid_image_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            response = requests.head(url, timeout=5)  # Send HEAD request to avoid downloading full image
            return response.status_code == 200
        except requests.RequestException:
            return False