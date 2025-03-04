import logging
import os
import json
from odoo import http
from odoo.http import request, Response
from odoo.addons.smartform.services.html_to_pdf import PDFService

_logger = logging.getLogger(__name__)

class SubmissionExportPDFController(http.Controller):

    @http.route('/submission/export/pdf', type='http', auth='public', methods=['POST'], csrf=False)
    def export_submission_pdf(self, **kwargs):
        try:
            # Extract 'ids' from the request body
            ids = kwargs.get('ids')
            if not ids:
                return self._error_response("Invalid Parameters: 'ids' are required.")

            # Fetch the submissions based on the provided IDs
            submission_ids = [int(id.strip()) for id in ids.split(',')]
            submissions = request.env['submission'].sudo().search([('id', 'in', submission_ids)])

            if not submissions:
                return self._error_response("No submissions found for the given IDs.")

            # Get the form hash from the first submission and fetch the form data
            form_hash = submissions[0].form_id
            pdf_service = PDFService()
            form_data = pdf_service.get_form_data(form_hash)

            # Generate the ZIP file containing PDFs
            zip_file = pdf_service.generate_pdfs_and_zip(form_data, submissions)

            # Serve the ZIP file for download
            return self._serve_zip_file(zip_file)

        except Exception as e:
            _logger.error(f"Error exporting PDFs: {str(e)}")
            return self._error_response(f"Error exporting PDFs: {str(e)}")

    def _error_response(self, message):
        return Response(
            json.dumps({'success': False, 'message': message}),
            status=400,
            headers=[('Content-Type', 'application/json')]
        )

    def _serve_zip_file(self, zip_file):
        try:
            with open(zip_file, 'rb') as f:
                data = f.read()

            # Clean up the temporary zip file after reading
            os.unlink(zip_file)

            # Properly serve the binary file with correct headers
            return Response(
                data,
                headers=[
                    ('Content-Type', 'application/zip'),
                    ('Content-Disposition', f'attachment; filename="{os.path.basename(zip_file)}"')
                ],
                status=200
            )
        except Exception as e:
            _logger.error(f"Error serving ZIP file: {str(e)}")
            return self._error_response(f"Error serving ZIP file: {str(e)}")
