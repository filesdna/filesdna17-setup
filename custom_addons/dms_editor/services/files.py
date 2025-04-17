
import base64
import logging
import json
import pytz
import os
import requests
import hashlib
from datetime import datetime, timedelta  
import fitz  # PyMuPDF for PDF modification
import random
import string
import subprocess

from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigFieldSpec
from pyhanko.sign.signers import PdfSignatureMetadata
from cryptography.hazmat.primitives import hashes

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.x509.oid import NameOID

from odoo import http
from odoo.http import request, Response
from odoo.tools import config
from odoo.exceptions import UserError
from odoo.addons.dms_editor.services.comment import CommentService
from odoo.addons.dms_editor.services.blockchain import BlockchainService
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.addons.dms_editor.services.pdf_editor import PdfEditorService
from odoo.addons.dms_editor.services.email_template import mail_data, create_log_note
from io import BytesIO

_logger = logging.getLogger(__name__)

server_path = config['server_path']
google_bucket = config=['google_bucket']
gcs_service = LocalStorageService()

class Files:
    def generate_images_with_hash(self, document_id, status, user_id=None):
        """Generate images with hash for the document."""
        try:
            # Fetch all images associated with the document
            all_images = request.env["document.images"].sudo().search([("document_id", "=", document_id)], order="order_by ASC")

            # Process each image
            result = []
            for item in all_images:
                get_obj = None

                # Retrieve JSON data if status is not "Pending Owner"
                # if status != "pending_owner":
                #     get_obj = request.env["document.data"].sudo().search([
                #         ("document_id", "=", document_id),
                #         ("page_id", "=", item.id)
                #     ], limit=1)

                objects = get_obj.json_data if get_obj else []

                # Generate hash keys
                hash_key = self._generate_random_hash(10)
                hash_key1 = self._generate_random_hash(10)

                # Create document load image entries
                request.env["document.load.img"].sudo().create([{
                    "doc_image_id": item.id,
                    "hash_key": hash_key,
                    "image_type": "F"
                }, {
                    "doc_image_id": item.id,
                    "hash_key": hash_key1,
                    "image_type": "T"
                }])

                # Retrieve comments (if user_id is provided)
                comment = CommentService()
                comments = comment.get_comments(item.id, user_id) if user_id else []

                # Append the image data to the result
                result.append({
                    "url": f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}/api/get-doc-data/{hash_key}",
                    "thumb_url": f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}/api/get-doc-data/{hash_key1}",
                    "id": item.id,
                    "order_by": item.order_by,
                    "objects": objects,
                    "comments": comments
                })

            return result

        except Exception as e:
            _logger.error(f"Error generating images with hash: {str(e)}")
            return []

    def _generate_random_hash(self, length=10):
        """Generate a random alphanumeric hash of the specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))



    def generate_new_pdf(self, get_file_data, status, user_id, is_guest, time_zone, email, ip, get_cuser, json_data):
            """
            Generate a new PDF with all signs and handle file updates, blockchain integration, and PDF signing.

            :param get_file_data: dict - File data (e.g., document details)
            :param hash_key: str - Hash key for the file
            :param pass_status: bool - Pass status
            :param status: str - Document status
            :param sign_status: bool - Whether the document is signed
            :param user_id: int - User ID
            :param is_guest: bool - Whether the user is a guest
            :param time_zone: str - Time zone
            :param email: str - Email of the user
            :param ip: str - IP address of the user
            :param get_cuser: dict - User context (e.g., team_id, home_directory)
            :param json_data: list - JSON data for the PDF
            :return: bool - Whether the operation was successful
            """
            try:
                # Paths and temporary folder setup
                temp_path = f'{server_path}/dms_editor/static/src/assets'
                pdf_editor = PdfEditorService()
                _logger.info("Starting PDF modification...")

                # Modify PDF content
                edited_pdf_name = pdf_editor.modify_pdf_content(json_data, get_file_data.id)
                _logger.info(f"{edited_pdf_name}...")

                # Sign the PDF if the user is not a guest
                if not is_guest:
                    self.sign_pdf(edited_pdf_name, get_cuser, ip, time_zone)
                    signed_pdf_path = os.path.join(temp_path, 'signpdf', edited_pdf_name)
                    pdf_path = signed_pdf_path
                else:
                    edited_pdf_path = os.path.join(temp_path, 'pdf', edited_pdf_name)
                    pdf_path = edited_pdf_path

                # Verify if the PDF exists
                if os.path.exists(pdf_path):
                    # Generate file hash
                    file_hash = self.file_hash(pdf_path, "file")

                    # Encryption key
                    encryption_key = request.env.user.company_id.encription_key

                    # Upload the PDF to a bucket
                    db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
                    destination = f'{db_name}/{get_file_data.attachment_id.store_fname}'
                    upload_response = self.upload_to_gcs(pdf_path, destination, encription=None)

                    # Handle file metadata and cleanup
                    if upload_response:
                        self.remove_all_images(get_file_data.id)
                        temp_image_path = os.path.join(temp_path, 'temp', get_file_data.name)
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)

                        # Prepare data for PDF generation
                        pdf_data = {
                            "document_id": get_file_data.id,
                            "user_id": get_file_data.create_uid.id,
                            "path": pdf_path,
                            "name": get_file_data.attachment_id.store_fname.split('/')[1],
                            "append_json": get_file_data.append_json,
                        }
                        self.generate_pdf_pages(pdf_data, encryption_key, status)

                        # Blockchain integration if the user is not a guest
                        if user_id:
                            if not is_guest:
                                bc = BlockchainService()
                                blockchain_data = {"user_id": user_id, "hash": file_hash}
                                bc_document = bc.add_document_in_blockchain(blockchain_data)
                                _logger.info(f"bc_document:{bc_document}")

                                # Update file metadata
                                write_result = request.env['dms.file'].sudo().search([
                                    ("id", "=", get_file_data.id)
                                ]).write({
                                    "sha512_hash": file_hash,
                                    "bc_document": bc_document,
                                    "write_uid": get_cuser['id']
                                })
                                test = request.env['document.version'].sudo().search([ ("document_id", "=", get_file_data.id) ]).write({ "sha512_hash": file_hash,"data_path":f"document/{file_hash}"})
                                _logger.info(f"test::{test}")
                                # Fetch the updated record
                                if write_result:
                                    updated_file_data = request.env['dms.file'].sudo().search([("id", "=", get_file_data.id)], limit=1)
                                    if updated_file_data:
                                        # Add signature to blockchain using the updated data
                                        bc_signature = bc.add_signature_in_blockchain(updated_file_data.sha512_hash, user_id)
                                    else:
                                        _logger.error(f"Failed to retrieve updated file data for ID {get_file_data.id}.")
                                        return self._response_error("Error retrieving updated file data.")
                                else:
                                    _logger.error(f"Failed to update file metadata for ID {get_file_data.id}.")
                                    return self._response_error("Error updating file metadata.")
                                # Add signature to blockchain
                                bc_signature = bc.add_signature_in_blockchain(updated_file_data.sha512_hash, user_id)
                                _logger.info(f"bc_signature:{bc_signature}")
                                self.document_sign_bc(user_id, updated_file_data.id, updated_file_data.sha512_hash, bc_document, bc_signature['signature'], email, updated_file_data.create_uid.id)
                        else:
                            # Update file metadata for guests
                            request.env['dms.file'].sudo().search([
                                ("id", "=", get_file_data.id)
                            ]).write({
                                "sha512_hash": file_hash,
                            })
                            test = request.env['document.version'].sudo().search([ ("document_id", "=", get_file_data.id) ]).write({ "sha512_hash": file_hash,"data_path":f"document/{file_hash}"})
                            _logger.info(f"test::{test}")
                    _logger.info("PDF generation and upload completed successfully.")
                    return True
                else:
                    _logger.error("PDF file does not exist.")
                    return False

            except Exception as e:
                _logger.error(f"Error generating new PDF: {str(e)}")
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


    def upload_to_gcs(self, file_path, destination,encription=True):
        """Upload file to Google Cloud Storage."""
        try:
            if encription:
                encryption_key = request.env.user.company_id.encription_key
            else:
                encryption_key = None
            # Prepare upload details
            

            # Initialize Google Cloud Storage service
            
            gcs_service.upload_file(file_path, destination, encryption_key)
            return True
        except Exception as e:
            _logger.error(f"Failed to upload JSON file to GCS: {str(e)}")
            return False
    
    def remove_all_images(self, document_id, remove_data=False):
        """
        Remove all files related to a document from the local storage and bucket.

        :param document_id: int - The ID of the document.
        :param remove_data: bool - Whether to delete records from the database.
        :return: bool - True on successful removal.
        """
        try:
            # Get all related images
            document_images = request.env['document.images'].sudo().search([('document_id', '=', document_id)])
            directory = f'{server_path}/dms_editor/static/src/assets/pdf/output'
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            for image in document_images:
                # Remove main URL file
                if image.url:
                    filename = image.url.split('/')[-1]
                    file_path = os.path.join(directory, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        _logger.info(f"Removed local file: {file_path}")

                    # Remove from bucket
                    self.remove_file_from_bucket(f"{db_name}/pdf_images/{filename}")

                # Remove thumbnail URL file
                if image.thumb_url:
                    thumb_filename = image.thumb_url.split('/')[-1]
                    thumb_path = os.path.join(directory, thumb_filename)
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                        _logger.info(f"Removed local file: {thumb_path}")

                    # Remove from bucket
                    # self.remove_file_from_bucket(f"{db_name}/pdf_images/{thumb_filename}")

            # Remove database records if specified
            if remove_data:
                document_images.unlink()  # Remove document_images records
                # request.env['document.data'].sudo().search([('document_id', '=', document_id)]).unlink()
                _logger.info(f"Removed database records for document_id: {document_id}")

            return True

        except Exception as e:
            _logger.error(f"Error removing images: {str(e)}")
            return False


    def remove_file_from_bucket(self, destination):
        """
        Remove a file from the storage bucket.
        :return: bool - True if removed successfully, False otherwise.
        """
        try:
            # Remove from Google Cloud Storage
            gcs_service.delete_file(destination)
            return True
        except Exception as e:
            _logger.error(f"Error removing file from bucket: {str(e)}")
            return False

    def generate_csr(self, private_key_path, user_email):
        """
        Generate a Certificate Signing Request (CSR) for the user.

        :param private_key_path: str - The path to the private key.
        :param user_email: str - The user's email.
        :return: str - Path to the generated CSR file.
        """
        csr_path = f"/tmp/{user_email}_request.csr"
        try:
            subprocess.check_call([
                "openssl", "req", "-new", 
                "-key", private_key_path, 
                "-out", csr_path,
                "-subj", f"/C=AE/ST=Dubai/L=Dubai/O=Borderless Security/CN={user_email}/emailAddress={user_email}",
                "-passin", "pass:filesdna"  # Provide the passphrase here
            ])
            _logger.info(f"CSR successfully generated at {csr_path}")
            return csr_path
        except subprocess.CalledProcessError as e:
            _logger.error(f"Error generating CSR: {str(e)}")
            return None

    def submit_csr_to_ca(self, csr_path, private_key_path):
        """
        Simulate submitting the CSR to a CA and returning a signed certificate.
        """
        ca_signed_cert_path = f"/tmp/{os.path.basename(csr_path).replace('.csr', '_cert.pem')}"
        try:
            # Use OpenSSL to self-sign the CSR for testing purposes
            subprocess.check_call([
                "openssl", "x509", "-req", "-days", "365",
                "-in", csr_path,
                "-signkey", private_key_path,
                "-out", ca_signed_cert_path,
                "-passin", "pass:filesdna"  # Provide the passphrase here
            ])
            _logger.info(f"CA-signed certificate generated at {ca_signed_cert_path}")
            return ca_signed_cert_path
        except subprocess.CalledProcessError as e:
            _logger.error(f"Error signing certificate: {str(e)}")
            return None

    def generate_p12_with_ca_certificate(self, private_key_path, user_email, ca_signed_cert_path, root_cert_path):
        """
        Generate a P12 certificate using private key, CA-signed certificate, and root certificate.

        :param private_key_path: str - Path to the user's private key.
        :param user_email: str - The user's email.
        :param ca_signed_cert_path: str - Path to the CA-signed certificate.
        :param root_cert_path: str - Path to the root certificate.
        :return: bool - True if successful, False otherwise.
        """
        try:
            p12_name = user_email.split("@")[0]
            tmp_dir = f'{server_path}/dms_editor/static/src/assets/p12'
            os.makedirs(tmp_dir, exist_ok=True)
            p12_file_path = os.path.join(tmp_dir, f"{p12_name}.p12")

            passphrase = "filesdna"  # Password for the `.p12` file
            your_private_key_passphrase = "filesdna"  # Passphrase for the private key
            
            # Ensure the necessary files exist
            if not os.path.exists(private_key_path) or not os.path.exists(ca_signed_cert_path) or not os.path.exists(root_cert_path):
                raise FileNotFoundError("Private key, CA-signed certificate, or root certificate file not found.")

            # Combine the private key, CA-signed certificate, and root certificate into a .p12 file
            subprocess.check_call([
                "openssl", "pkcs12", "-export",
                "-inkey", private_key_path,  # Path to the user's private key
                "-in", ca_signed_cert_path,  # Path to the CA-signed certificate
                "-certfile", root_cert_path,  # Root certificate file
                "-out", p12_file_path,  # Output `.p12` file
                "-passout", f"pass:{passphrase}",  # Password for the `.p12` file
                "-passin", f"pass:{your_private_key_passphrase}",  # Passphrase for private key
                "-certpbe", "AES-256-CBC",  # Strong encryption for certificates
                "-keypbe", "AES-256-CBC"  # Strong encryption for keys
            ])

            _logger.info(f"P12 file successfully generated at {p12_file_path}")
            return p12_file_path

        except subprocess.CalledProcessError as e:
            _logger.error(f"Error generating P12 file: {str(e)}")
            return False
        except Exception as e:
            _logger.error(f"Error in generate_p12_with_ca_certificate: {str(e)}")
            return False

    def generate_p12(self, email):
        directory = f'{server_path}/dms_editor/static/src/'
        user_name = email.split("@")[0]
        try:
            # Ensure directories exist
            private_dir = os.path.join(directory, 'assets', 'private')
            certs_dir = os.path.join(directory, 'assets', 'certs')
            p12_dir = os.path.join(directory, 'assets', 'p12')

            os.makedirs(private_dir, exist_ok=True)
            os.makedirs(certs_dir, exist_ok=True)
            os.makedirs(p12_dir, exist_ok=True)

            # Paths for key and cert files
            key_path = os.path.join(private_dir, f"{user_name}.key")
            cert_path = os.path.join(certs_dir, f"{user_name}.crt")
            p12_path = os.path.join(p12_dir, f"{user_name}.p12")

            root_cert_path = os.path.join(directory, 'key', 'root.crt')
            intermediate_cert_path = os.path.join(directory, 'key', 'intermediate.crt')

            # Load root and intermediate certificates
            with open(root_cert_path, "rb") as root_file:
                root_cert = x509.load_pem_x509_certificate(root_file.read())
            with open(intermediate_cert_path, "rb") as intermediate_file:
                intermediate_cert = x509.load_pem_x509_certificate(intermediate_file.read())

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Save private key
            with open(key_path, "wb") as key_file:
                key_file.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Generate user certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, email),
            ])
            certificate = x509.CertificateBuilder() \
                .subject_name(subject) \
                .issuer_name(issuer) \
                .public_key(private_key.public_key()) \
                .serial_number(int(datetime.utcnow().timestamp())) \
                .not_valid_before(datetime.utcnow()) \
                .not_valid_after(datetime.utcnow() + timedelta(days=365)) \
                .sign(private_key, SHA256())

            # Save user certificate
            with open(cert_path, "wb") as cert_file:
                cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))

            # Create PKCS12 with root and intermediate certificates
            p12 = serialization.pkcs12.serialize_key_and_certificates(
                name=email.encode(),
                key=private_key,
                cert=certificate,
                cas=[intermediate_cert, root_cert],
                encryption_algorithm=serialization.BestAvailableEncryption(b"filesdna"),
            )

            # Save PKCS12
            with open(p12_path, "wb") as p12_file:
                p12_file.write(p12)

            return True
        except Exception as e:
            _logger.error(f"Error generating P12: {str(e)}")
            return False


    def sign_pdf(self, file_name, user_details, ip, timezone=""):
        try:
            tmp_dir = f'{server_path}/dms_editor/static/src/assets'

            # Validate and sanitize file name
            if not file_name or '\0' in file_name or any(c in file_name for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                raise ValueError("Invalid file name provided.")
            pdf_path = os.path.abspath(os.path.join(tmp_dir, 'pdf', file_name))
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            user_name = f"{user_details.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            time_zone = timezone or "Europe/London"
            local_time = datetime.now(pytz.timezone(time_zone))
            date_time = local_time.strftime("%B %d, %Y, %H:%M")
            sign_reason = f"Digital Signature | {user_details.email}, {ip}, {date_time}"

            # Read the PDF
            with open(pdf_path, "rb") as pdf_file:
                pdf_buffer = pdf_file.read()

                # Check if the file starts with the PDF signature
                if pdf_buffer[:4] != b'%PDF':
                    raise ValueError("The file is not a valid PDF.")

            # Modify the PDF content
            modified_pdf_buffer = self.modified_pdf_buffers(pdf_buffer, sign_reason, file_name, user_details.id)

            # Check or generate the P12 certificate
            p12_name = user_details.email.split("@")[0]
            p12_path = os.path.join(tmp_dir, 'p12', f"{p12_name}.p12")
            if not os.path.exists(p12_path):
                if not self.generate_p12(user_details.email):
                    _logger.error(f"Failed to generate P12 for {user_details.email}")
                    return False

            # Load the signer
            try:
                signer = signers.SimpleSigner.load_pkcs12(
                    pfx_file=p12_path,
                    passphrase=b"filesdna"
                )
            except Exception as e:
                _logger.error(f"Error loading signer: {str(e)}")
                return False

            # Create IncrementalPdfFileWriter from the modified PDF buffer
            pdf_writer = IncrementalPdfFileWriter(BytesIO(modified_pdf_buffer))

            # Prepare the signature metadata
            signature_meta = PdfSignatureMetadata(field_name=user_name, reason=sign_reason, location=time_zone)
            
            # Optional: Create a new signature field spec (if necessary)
            new_field_spec = SigFieldSpec(sig_field_name=user_name)

            # Sign the PDF using signer.sign_pdf()
            try:
                signed_pdf_stream = signers.sign_pdf(
                    pdf_out=pdf_writer,
                    signature_meta=signature_meta,
                    signer=signer,
                    new_field_spec=new_field_spec,
                    in_place=False  # False means we output to a BytesIO object
                )

                # Write the signed PDF to a file
                signed_pdf_path = os.path.join(tmp_dir, 'signpdf', file_name)
                os.makedirs(os.path.dirname(signed_pdf_path), exist_ok=True)
                with open(signed_pdf_path, "wb") as signed_pdf_file:
                    signed_pdf_file.write(signed_pdf_stream.read())

            except Exception as e:
                _logger.error(f"Error signing PDF: {str(e)}")
                return False

            return True

        except Exception as e:
            _logger.error(f"Error signing PDF {file_name}: {str(e)}")
            return False

    def modified_pdf_buffers(self, buffer, reason, file_name, user_id):
        """
        Modify a PDF buffer to include signature placeholders and metadata.

        :param buffer: bytes - PDF file content as bytes.
        :param reason: str - Reason for signing.
        :param file_name: str - Name of the file being processed.
        :param user_id: int - ID of the user.
        :return: bytes - Modified PDF content.
        """
        try:
            user = request.env['res.users'].sudo().browse(user_id)
            base_path = f'{server_path}/dms_editor/static/src'
            tmp_path = os.path.join(base_path, 'assets', 'signpdf')
            os.makedirs(tmp_path, exist_ok=True)

            SIGNATURE_LENGTH = 4096

            # Read the PDF file from the buffer
            doc = fitz.open(stream=buffer, filetype="pdf")
            page = doc[0]  # Assuming we're modifying the first page

            # Add signature placeholder
            rect = fitz.Rect(50, 50, 200, 100)  # Placeholder rectangle for signature
            signature_placeholder = "A" * SIGNATURE_LENGTH
            page.insert_textbox(rect, signature_placeholder, fontsize=8)

            # Add metadata
            doc.set_metadata({
                'title': file_name,
                'author': user.name,
                'subject': reason,
                'keywords': f'signature, {user.email}',
                'creator': user.name,
                'producer': 'FilesDNA PDF Editor',
                'modDate': datetime.now().strftime("D:%Y%m%d%H%M%S"),  # Proper format for PDF metadata
            })

            # Save the modified PDF
            modified_pdf_path = os.path.join(tmp_path, f"{file_name}_{datetime.now().timestamp()}.pdf")
            doc.save(modified_pdf_path)

            # Read back the modified PDF content
            with open(modified_pdf_path, "rb") as modified_pdf_file:
                modified_pdf_content = modified_pdf_file.read()

            # Cleanup temporary file
            os.remove(modified_pdf_path)

            return modified_pdf_content

        except Exception as e:
            _logger.error(f"Error modifying PDF buffers: {str(e)}")
            raise UserError(f"Error modifying PDF: {str(e)}")



    def download_file(self, destination, local_path):
        """Retrieve append data."""
        try:
            # Define path for JSON retrieval based on the environment setup
            if os.path.exists(local_path):
                os.remove(local_path)

            
            key = request.env.user.company_id.encription_key
            
            gcs_service.download_file(destination, local_path, encryption_key=key)
        except Exception as e:
            _logger.error(f"Error downloading file: {str(e)}")
            return False

    def generate_pdf_pages(self, set_data, key, status):
        try:
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            folder_path = f"{server_path}/dms_editor/static/src/assets/pdf/output/"
            os.makedirs(folder_path, exist_ok=True)

            document_id = set_data["document_id"]
            name = set_data["name"]
            user_id = set_data["user_id"]
            path = set_data["path"]
            append_json = set_data.get("append_json")

            document = request.env["dms.file"].sudo().search([("id", "=", document_id)])
            if not document:
                _logger.error("Document not found.")
                return False
            document.write({"document_status": "Preparing"})

            doc = fitz.open(path)
            _logger.info(f"request.env.company.id:{request.env.company.id}")
            url_path = f"https://storage.cloud.google.com/{google_bucket}/{db_name}/pdf_images"
            user = request.env["res.users"].sudo().browse(user_id)

            for page_number in range(len(doc)):
                page = doc[page_number]
                image_path = os.path.join(folder_path, f"{name}_{page_number + 1}.png")
                thumb_path = os.path.join(folder_path, f"{name}_{page_number + 1}_thumb.png")

                pix = page.get_pixmap(dpi=72)
                pix.save(image_path)

                # Apply scaling using fitz.Matrix
                # matrix = fitz.Matrix(0.25, 0.25)  # Scale down to 25%
                # thumb_pix = page.get_pixmap(matrix=matrix, dpi=200)  # Apply scaling while rendering
                # thumb_pix.save(thumb_path)

                destination = f"{db_name}/pdf_images/{image_path.split('output/')[1]}"
                uploaded_file = self.upload_to_gcs(image_path, destination, encription=None)

                document_image = request.env["document.images"].sudo().search([
                    ("document_id", "=", document_id),
                    ("user_id", "=", user_id),
                    ("order_by", "=", page_number + 1)
                ])
                if document_image:
                    document_image.write({
                        "url": f"{url_path}/{os.path.basename(image_path)}",
                        "thumb_url": f"{url_path}/{os.path.basename(thumb_path)}",
                        "file_data": uploaded_file,
                        "order_by": page_number + 1
                    })
                else:
                    request.env["document.images"].sudo().create({
                        "order_by": page_number + 1,
                        "url": f"{url_path}/{os.path.basename(image_path)}",
                        "thumb_url": f"{url_path}/{os.path.basename(thumb_path)}",
                        "file_data": uploaded_file,
                        "document_id": document_id,
                        "user_id": user_id
                    })

            document.write({"document_status": status or "Pending"})

            if status == "Completed":
                self.remove_file_from_bucket(f"{db_name}/append_jsons/{append_json}")
                document.write({"append_json": None})

                request.env["dms.json.version"].sudo().search([
                    ("document_id", "=", document_id),
                    ("version", "!=", document.json_version)
                ]).unlink()

                self._send_c_copies(document)

            return True

        except Exception as e:
            _logger.error(f"Error generating PDF pages: {str(e)}")
            return False



    def _send_c_copies(self, data):
        """
        Send copies of a document to users and manage document images.

        :param data: dict - Document metadata and details.
        :return: bool - True if successful, False otherwise.
        """
        try:
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            document_id = data.id
            full_name = data.attachment_id.store_fname
            pictures = []

            get_doc_img = request.env["document.images"].sudo().search(
                [("document_id", "=", document_id)], order="order_by"
            )
            d_path = f"{server_path}/dms_editor/static/src/temp"
            os.makedirs(d_path, exist_ok=True)

            # Download the main document
            try:
                
                destination_path = f"{db_name}/{full_name}"
                
                gcs_service.download_file(destination_path, os.path.join(d_path, full_name.split('/')[1]), encryption_key=None)
            except Exception as e:
                _logger.error(f"Error downloading main document: {str(e)}")
                return False

            # Download document images and thumbnails
            for item in get_doc_img:
                image_name = os.path.basename(item.url)
                thumb_name = os.path.basename(item.thumb_url)

                # Download images
                
                
                gcs_service.download_file(f"{db_name}/pdf_images/{image_name}", os.path.join(d_path, image_name), encryption_key=None)
                # gcs_service.download_file(f"{db_name}/pdf_images/{thumb_name}", os.path.join(d_path, thumb_name), encryption_key=None)

                pictures.append({
                    "url": os.path.join(d_path, image_name),
                    "thumb_url": os.path.join(d_path, thumb_name),
                    "order_by": item.order_by,
                })

            all_images = {
                "pictures": pictures,
                "lPath": os.path.join(d_path, full_name.split('/')[1]),
            }

            # Get document signers
            get_list = request.env["document.sign"].sudo().search(
                [("document_id", "=", document_id)],
                order="order_by ASC",
            )
            
            for item in get_list:
                if item.email != item.sent_by_email:
                    self._send_guest_copy(data, item.email)

            _logger.info(f"deleting temp files...")
            # Cleanup temporary files
            self._delete_temp_files([all_images["lPath"]])
            self._delete_temp_files([pic["url"] for pic in pictures])
            # self._delete_temp_files([pic["thumb_url"] for pic in pictures])

            return True

        except Exception as e:
            _logger.error(f"Error sending carbon copies: {str(e)}")
            return False

    def _delete_temp_files(self, file_paths):
        """
        Delete temporary files.

        :param file_paths: list - List of file paths to delete.
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    _logger.info(f"Deleted temporary file: {file_path}")
            except Exception as e:
                _logger.error(f"Error deleting temporary file {file_path}: {str(e)}")


    def _send_guest_copy(self, data, email):
        """
        Send a completed document to a guest via email.

        :param data: dict - Document metadata and details.
        :param email: str - Guest's email address.
        :return: bool - True if successful, False otherwise.
        """
        try:
            db_name= request.env['ir.config_parameter'].sudo().get_param('web.base.url').split("//")[-1].split(".")[0]
            name = data.name
            full_name = data.attachment_id.store_fname
            pdf_path = f"{server_path}/dms_editor/static/src/temp"
            local_pdf_path = os.path.join(pdf_path, full_name.split('/')[1])

            # Download the document from the storage bucket
            
            destination_path = f"{db_name}/{full_name}"
            
            gcs_service.download_file(destination_path, local_pdf_path, encryption_key=None)

            # Fetch user details
            user_data = request.env["res.users"].sudo().search([("id", "=", data.create_uid.id)], limit=1)

            if not user_data:
                _logger.error("User details not found.")
                return False

            requester_name = user_data.name

            mail_data(
                email_type="completed_document", 
                subject=f"Completed Document - FilesDNA", 
                email_to=email, 
                header="Hi There,", 
                description=f"You received a file from <b>{requester_name}</b>.",
                hash_key=None,
                attachment_data=self._get_attachment_data(local_pdf_path),
                attachment_name=name
            )                
            
            create_log_note(data.id,"Document is completed")

            _logger.info(f"Guest copy of {full_name} sent to {email}.")
            return True

        except Exception as e:
            _logger.error(f"Error sending guest copy: {str(e)}")
            return False

    def _get_attachment_data(self, file_path):
        """
        Convert a file to base64 for attachment.

        :param file_path: str - Path to the file.
        :return: str - Base64-encoded file content.
        """
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            _logger.error(f"Error reading file for attachment: {str(e)}")
            return ""

    def document_sign_bc(self, user_id, document_id, hash_value, bc_document, bc_signature, email, owner_id):
        """
        Add or update a blockchain record for a user.

        :param user_id: ID of the user
        :param document_id: ID of the document
        :param hash_value: Hash value of the document
        :param bc_document: Blockchain document (JSON or text)
        :param bc_signature: Blockchain signature
        :param email: User's email
        :param owner_id: ID of the owner
        :return: The created or updated blockchain record
        """
        blockchain_record = request.env['document.sign.bc'].sudo().search([
            ('user_id', '=', user_id),
            ('document_id', '=', document_id),
            ('email', '=', email)
        ], limit=1)

        if blockchain_record:
            # Update the existing record
            blockchain_record.sudo().write({
                'hash_value': hash_value,
                'bc_document': bc_document if bc_document else '',
                'bc_signature': bc_signature,
                'date': datetime.now(),
            })
        else:
            # Create a new record
            blockchain_record = request.env['document.sign.bc'].sudo().create({
                'user_id': user_id,
                'document_id': document_id,
                'hash_value': hash_value,
                'bc_document': bc_document if bc_document else '',
                'bc_signature': bc_signature,
                'email': email,
                'owner_id': owner_id,
                'date': datetime.now(),
            })

        return blockchain_record
