# -*- coding: utf-8 -*-
from odoo import http
import logging
import requests
import os
import math
import odoo
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
import json
import base64
from werkzeug.utils import redirect
from odoo import http
import werkzeug.exceptions
from odoo.http import Response
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)

_logger = logging.getLogger(__name__)


class AttachmentAPI(http.Controller):

    @http.route('/api/user-companies', auth='user', type='json', methods=['GET'], csrf=True)
    def company_list(self, **kw):
        result = []
        user = request.env.user
        company_ids = user.company_ids  # All companies the user has access to
        default_company = user.company_id  # The default (active) company

        _logger.info('Allowed Companies: %s', company_ids)

        for company_id in company_ids:
            result.append({
                'company_name': company_id.name,
                'company_id': company_id.id,
                'is_default': company_id.id == default_company.id  # True if this is the default company
            })

        success_message = {'success': True, 'message': result}
        return success_message

    @http.route('/api/attachments', auth='user', type='json', methods=['POST'], csrf=False)
    def list(self, **kw):
        uid = request.env.user.id
        page_number = int(kw.get('page', 1))
        page_limit = int(kw.get('per_page', 10))
        directory_id = int(kw.get('directory_id'))
        is_deleted = False
        offset = (page_number - 1) * page_limit
        if offset < 0:
            message = {'success': False, 'message': 'page number not exist'}
            return werkzeug.exceptions.abort(Response(json.dumps(message), status=404))
        domain = [('is_deleted', '=', is_deleted), ('directory_id', '=', directory_id)]
        file_model = request.env['dms.file'].sudo()
        files = file_model.search(domain, limit=page_limit, offset=offset, order='name asc')
        if not files:
            message = {'success': True, 'message': 'No file found with the provided User ID'}

            return werkzeug.exceptions.abort(Response(json.dumps(message), status=200))

        # Prepare the result list
        result = []
        for file in files:
            tags = [{'id': tag.id, 'name': tag.name} for tag in file.tag_ids]
            if file.active_security:
                if file.security_user_id.id == uid:
                    result.append({
                        'file_id': file.id,
                        'file_name': file.name,
                        'directory': file.directory_id.name,
                        'directory_id': file.directory_id.id,
                        'file_version': file.current_version_id.version_number,
                        'stored_filename': file.attachment_ids.store_fname,
                        'file_type': file.attachment_ids.mimetype,
                        'size': file.attachment_ids.file_size,
                        'created_on': file.create_date.strftime('%Y-%m-%d %H:%M:%S') if file.create_date else '',
                        'modified_on': file.write_date.strftime('%Y-%m-%d %H:%M:%S') if file.write_date else '',
                        'modified_by': file.write_uid.name,
                        'created_by': file.create_uid.name,
                        'company_id': file.company_id.name,
                        'tags': tags
                    })
            else:
                result.append({
                    'file_id': file.id,
                    'file_name': file.name,
                    'directory': file.directory_id.name,
                    'directory_id': file.directory_id.id,
                    'file_version': file.current_version_id.version_number,
                    'stored_filename': file.attachment_ids.store_fname,
                    'file_type': file.attachment_ids.mimetype,
                    'size': file.attachment_ids.file_size,
                    'created_on': file.create_date.strftime('%Y-%m-%d %H:%M:%S') if file.create_date else '',
                    'modified_on': file.write_date.strftime('%Y-%m-%d %H:%M:%S') if file.write_date else '',
                    'created_by': file.create_uid.name,
                    'company_id': file.company_id.name,
                    'tags': tags
                })

        total_count = file_model.search_count(domain)
        response = {'attachments': result,
                    "total_count": total_count,
                    "total_pages": math.ceil(file_model.search_count(domain) / page_limit),
                    "per_page": page_limit,
                    "page": page_number, 'success': True}
        return response

    # /////////////////////////////////////// trash API //////////////////////////////////////////////////////////

    @http.route('/api/attachments/move-trash', auth='user', type='json', methods=['POST'], csrf=False)
    def trash(self, **kw):
        file_id = int(kw.get('file_id'))
        domain = [('id', '=', file_id), ('is_deleted', '=', False)]
        file_model = request.env['dms.file'].sudo()
        file = file_model.search(domain)
        if file:
            file.unlink_file()
            file_name = file.attachment_ids.name
            success_message = {'success': True, 'message': f"file {file_name} has moved to recycle bin"}
            return success_message
        else:
            message = {'success': False, 'message': 'No file found with the provided ID'}
            return werkzeug.exceptions.abort(Response(json.dumps(message), status=404))

    # ///////////////////////////////// restore API ////////////////////////////////////////////////////////////////////

    @http.route('/api/attachments/restore-trash', auth='user', type='json', methods=['POST'], csrf=False)
    def restore(self, **kw):
        file_id = int(kw.get('file_id'))
        domain = [('id', '=', file_id), ('is_deleted', '=', True)]
        file_model = request.env['dms.file'].sudo()
        file = file_model.search(domain)
        if file:
            file.action_restore_file()
            file_name = file.attachment_ids.name
            success_message = {'success': True, 'message': f"file {file_name} has restored from recycle bin"}
            return success_message
        else:
            message = {'success': False, 'message': 'No file found with the provided ID in recycle bin'}
            return werkzeug.exceptions.abort(Response(json.dumps(message), status=404))

    # ////////////////////////////////////// Rename ////////////////////////////////////////////////////////////

    @http.route('/api/attachments/rename-file', auth='user', type='json', methods=['POST'], csrf=False)
    def rename_file(self, **kw):
        # Retrieve the file ID and new name from the payload
        file_id = kw.get('file_id')
        new_name = kw.get('new_name')

        if not file_id or not new_name:
            # Return an error response if file_id or new_name are missing
            error_message = {'success': False, 'message': 'Missing file ID or new name in the request'}
            return request.werkzeug.exceptions.abort(Response(json.dumps(error_message), status=400))

        try:
            file_id = int(file_id)
        except ValueError:
            # Handle case where file_id is not an integer
            error_message = {'success': False, 'message': 'file ID must be an integer'}
            return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=400))

        # Define the search domain
        domain = [('id', '=', file_id), ('is_deleted', '=', False)]

        # Access the file model
        file_model = request.env['dms.file'].sudo()
        file = file_model.search(domain)

        if file:
            # Update the file's name if it is found
            file.name = f"{new_name}.{file.extension}"
            success_message = {'success': True, 'message': "File has been renamed successfully."}
            return success_message
        else:
            # Return a 404 response if no file is found
            error_message = {'success': False, 'message': 'No file found with the provided ID'}
            return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=404))

    # /////////////////////////////////// upload new file ////////////////////////////////////////////////
    @http.route('/api/attachments/upload-file', type='json', auth='user', methods=['POST'])
    def upload_file(self, **post):
        file_data = post.get('file_data')
        file_name = post.get('file_name')
        directoryId = post.get('directory_id')
        reference_id = post.get('reference_id')
        file_extension = os.path.splitext(file_name)[1].replace('.', '').lower()

        directory_id = request.env['dms.directory'].sudo().search([('id', '=', directoryId)])
        if not file_data or not file_name or not directory_id:
            error_message = {'success': False, 'error': 'No file provided'}
            return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=404))

        file_content = base64.b64decode(file_data)

        # 🔹 Fetch default reference
        default_reference = request.env['dms.reference'].sudo().search([], limit=1)
        if not default_reference:
            return {
                'success': False,
                'error': 'No default reference found. Please create one first.'
            }

        # 🔹 Use provided reference or fallback to default
        file = request.env['dms.file'].create({
            "name": file_name,
            'directory_id': directory_id.id,
            'content': base64.b64encode(file_content),
            'create_uid': request.env.user.id,
            'storage_id': directory_id.storage_id.id,
            'company_id': directory_id.company_id.id,
            'reference_id': int(reference_id) if reference_id else default_reference.id,
            'extension': file_extension,  # ✅ Set extension here
        })

        file._compute_count_itrack()

        return {
            'success': True,
            'message': f'File uploaded successfully on Company {directory_id.company_id.name}',
            'file': file.name
        }

    # ///////////////////////////////// Download File ///////////////////////////////////////////
    @http.route('/api/attachment/download/<int:attachment_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_attachment(self, attachment_id):
        # Retrieve the attachment record
        uid = request.env.user.id
        attachment = request.env['dms.file'].sudo().browse(attachment_id)
        if not attachment.exists():
            return Response("Attachment not found", status=404)
        if attachment.active_security:
            if attachment.security_user_id.id != uid:
                return Response(f"Unathourized, this file is locked by user {attachment.security_user_id.name}",
                                status=403)
        # Prepare the file for download
        file_data = attachment.attachment_ids.datas
        file_name = attachment.attachment_ids.name
        file_content = base64.b64decode(file_data)

        # Create the response
        response = request.make_response(
            file_content,
            headers=[
                ('Content-Type', attachment.attachment_ids.mimetype),
                ('Content-Disposition', f'attachment; filename="{file_name}"')
            ]
        )
        return response

    # ///////////////////////////////// directories //////////////////////////////////////
    @http.route('/api/attachments/directories/<int:company_id>', auth='user', type='json', methods=['GET'], csrf=False)
    def dir_list(self, company_id=None):
        uid = request.env.user.id
        result = []

        # Fetch access groups for the given company
        access_groups = request.env['dms.access.group'].search([('company_id', '=', company_id)])

        for group in access_groups:
            if uid in group.users.ids:
                for dir in group.directory_ids:
                    sub = bool(dir.child_directory_ids)  # Check if there are subdirectories

                    # Get parent directory ID safely
                    parent_id = dir.parent_id.id if dir.parent_id else None

                    # Check security access
                    # Check security access
                    if dir.is_root_directory and not dir.is_template:
                        if dir.active_security and dir.security_user_id.id == uid:
                            file_count = request.env['dms.file'].search_count([('directory_id', '=', dir.id)])
                            result.append({
                                "directory_name": dir.name,
                                "directory_id": dir.id,
                                "parent_id": parent_id,
                                "is_sub": sub,
                                "file_count": file_count,  # ✅ Add file count here
                                "perm": {
                                    "perm_create": group.perm_create,
                                    "perm_write": group.perm_write,
                                    "perm_download": group.perm_download,
                                    "perm_lock": group.perm_lock,
                                    "perm_rename": group.perm_rename,
                                    "perm_delete": group.perm_unlink,
                                    "perm_full_admin": group.perm_full_admin,
                                }
                            })
                        elif not dir.active_security:
                            file_count = request.env['dms.file'].search_count([('directory_id', '=', dir.id)])
                            result.append({
                                "directory_name": dir.name,
                                "directory_id": dir.id,
                                "parent_id": parent_id,
                                "is_sub": sub,
                                "file_count": file_count,  # ✅ Add file count here
                                "perm": {
                                    "perm_create": group.perm_create,
                                    "perm_write": group.perm_write,
                                    "perm_download": group.perm_download,
                                    "perm_lock": group.perm_lock,
                                    "perm_rename": group.perm_rename,
                                    "perm_delete": group.perm_unlink,
                                    "perm_full_admin": group.perm_full_admin,
                                }
                            })

        return {"success": True, "directories": result}

    # ///////////////////////////// fetch trash ////////////////////////////////////////////

    @http.route('/api/attachments/trash-list', auth='user', type='json', methods=['POST'], csrf=False)
    def trash_list(self, **kw):
        # return user id
        uid = request.env.user.id
        # Retrieve page number and page limit from the parameters or set defaults
        page_number = int(kw.get('page', 1))
        page_limit = int(kw.get('per_page', 10))
        company_id = int(kw.get('company_id'))
        is_deleted = True
        # Compute the offset for the search
        offset = (page_number - 1) * page_limit
        if offset < 0:
            message = {'success': False, 'message': 'page number not exist'}
            return werkzeug.exceptions.abort(Response(json.dumps(message), status=404))
        # Search for files belonging to the specified user
        domain = [('is_deleted', '=', is_deleted), ('company_id', '=', company_id)]
        file_model = request.env['dms.file'].sudo()

        files = file_model.search(domain, limit=page_limit, offset=offset, order='name asc')
        # If no files are found, return a 404 response
        if not files:
            if is_deleted:
                message = {'success': True, 'message': 'No files in recycle bin for provided user ID'}
            else:
                message = {'success': True, 'message': 'No file found with the provided User ID'}

            return werkzeug.exceptions.abort(Response(json.dumps(message), status=200))

        # Prepare the result list
        result = []
        for file in files:
            result.append({
                'file_id': file.id,
                'file_name': file.name,
                'directory': file.directory_id.name,
                'directory_id': file.directory_id.id,
                'stored_filename': file.attachment_ids.store_fname,
                'file_type': file.attachment_ids.mimetype,
                'size': file.attachment_ids.file_size,
                'created_on': file.create_date,
                'modified_on': file.write_date,
                'created_by': file.create_uid.name,
                'company_id': file.company_id.name

            })

        # Return the final response
        total_count = file_model.search_count(domain)
        response = {'attachments': result,
                    "total_count": total_count,
                    "total_pages": math.ceil(file_model.search_count(domain) / page_limit),
                    "per_page": page_limit,
                    "page": page_number, 'success': True}
        return response

    # /////////////////////////////////////// empty trash API //////////////////////////////////////////////////////////

    @http.route('/api/attachments/empty-trash/<int:file_id>', auth='user', type='json', methods=['POST'], csrf=False)
    def trash_empty(self, file_id=None):
        file = request.env[''].search([('id', '=', file_id)])
        if file_id == None:
            domain = [('is_deleted', '=', True), ('company_id', '=', file.company_id.id)]
        else:
            domain = [('id', '=', file_id), ('is_deleted', '=', True)]
        file_model = request.env['dms.file'].sudo()
        file = file_model.search(domain)
        if file:
            file.unlink()
            # file_name = file.attachment_ids.name
            success_message = {'success': True, 'message': f"file has been deleted"}
            return success_message
        else:
            error_message = {'success': False, 'message': f"file has been deleted"}
            return werkzeug.exceptions.abort(Response(json.dumps(error_message), status=404))

    # //////////////////////////// document versioning //////////////////////////////////////////////////////////////////////////

    @http.route('/api/attachments/file-version', auth='user', type='json', methods=['POST'], csrf=False)
    def document_version(self, **kw):
        file_data = kw.get('file_data')
        file_id = kw.get('file_id')
        if not file_data or not file_id:
            error_message = {'success': False, 'message': f"No file found"}
            return error_message
        domain = [('id', '=', file_id), ('is_deleted', '=', False)]
        file_model = request.env['dms.file'].sudo()
        file = file_model.search(domain)
        file.is_uploaded = True
        file_content = base64.b64decode(file_data)
        attachment = request.env['ir.attachment'].create({
            'name': file.name,
            'type': 'binary',
            'datas': base64.b64encode(file_content),  # Encode the content to base64
            'res_model': 'dms.file',  # The model to which the attachment is related
            'res_id': file_id,  # The ID of the record to which the attachment is related

        })
        file._create_new_version([attachment.id])
        success_message = {'success': True, 'message': "file has been updated"}
        return success_message

    # //////////////////////////// check file name //////////////////////////////////////////////////////////////////////////

    @http.route('/api/attachments/file-check/<string:file_name>', auth='user', type='json', methods=['POST'],
                csrf=False)
    def check_file(self, file_name=None, **kw):
        uid = request.env.user.id
        company_id = kw.get('company_id')
        dir_result = []
        # Retrieve page number and page limit from the parameters or set defaults
        access_group = request.env['dms.access.group'].search([('company_id', '=', company_id)])
        for group in access_group:
            if uid in group.users.ids:
                for dir in group.directory_ids:
                    if dir.child_directory_ids.ids:
                        sub = True
                    else:
                        sub = False
                    if dir.is_root_directory:
                        dir_result.append(dir.id)
        domain = [('name', '=', file_name), ('is_deleted', '=', False), ('directory_id.id', 'in', dir_result),
                  ('company_id', '=', company_id)]
        file_model = request.env['dms.file'].sudo()
        file = file_model.search(domain)
        if file:
            success_message = {'success': True, 'message': "file exist"}
            return success_message
        else:
            error_message = {'success': False, 'message': "file not exist"}
            return error_message

    # ///////////////////////////////// sub directories //////////////////////////////////////
    @http.route('/api/attachments/sub-directories/<int:parent_dir>', auth='user', type='json', methods=['GET'],
                csrf=False)
    def sub_dir_list(self, parent_dir=None):
        result = []
        uid = request.env.user.id

        # Fetch subdirectories that belong to the given parent directory
        sub_dirs = request.env['dms.directory'].search([
            ('is_root_directory', '=', False),
            ('parent_id', '=', parent_dir)
        ])

        for sub_dir in sub_dirs:
            sub = bool(sub_dir.child_directory_ids)  # Check if subdirectories exist

            # 🔢 Count files in this directory
            files_count = request.env['dms.file'].search_count([
                ('directory_id', '=', sub_dir.id)
            ])

            data = {
                "directory_name": sub_dir.name,
                "directory_id": sub_dir.id,
                "parent_id": sub_dir.parent_id.id if sub_dir.parent_id else None,
                "is_sub": sub,
                "file_count": files_count,  # ✅ Added files count
            }
            result.append(data)

        return {"success": True, "directories": result}

    # //////////////////////////////////////// Search Result ///////////////////////////////////////////////////

    @http.route('/api/attachments/search-result/<int:company_id>', auth='user', type='json', methods=['POST'],
                csrf=False)
    def list_search(self, company_id=None, **kw):
        uid = request.env.user.id
        page_number = int(kw.get('page', 1))
        page_limit = int(kw.get('per_page', 10))
        is_deleted = False
        offset = (page_number - 1) * page_limit

        if offset < 0:
            message = {'success': False, 'message': 'Page number not exist'}
            return werkzeug.exceptions.abort(Response(json.dumps(message), status=404))

        # Base domain
        domain = [('is_deleted', '=', is_deleted), ('company_id', '=', company_id)]

        # Apply search criteria based on parameters provided
        search_name = kw.get('name')
        search_tag = kw.get('tag_name')
        search_type = kw.get('file_type')

        if search_name:
            domain.append(('name', 'ilike', search_name))
            print(domain)

        if search_tag:
            domain.append(('tag_ids.name', 'ilike', search_tag))

        if search_type:
            domain.append(('attachment_ids.mimetype', 'ilike', search_type))

        file_model = request.env['dms.file'].sudo()
        files = file_model.search(domain, limit=page_limit, offset=offset, order='name asc')

        if not files:
            message = {'success': True, 'message': 'No file found with the provided criteria'}
            return werkzeug.exceptions.abort(Response(json.dumps(message), status=200))

        # Prepare the result list
        result = []
        for file in files:
            tags = [{'id': tag.id, 'name': tag.name} for tag in file.tag_ids]
            file_info = {
                'file_id': file.id,
                'file_name': file.name,
                'directory': file.directory_id.name,
                'directory_id': file.directory_id.id,
                'file_version': file.current_version_id.version_number,
                'stored_filename': file.attachment_ids.store_fname,
                'file_type': file.attachment_ids.mimetype,
                'size': file.attachment_ids.file_size,
                'created_on': file.create_date,
                'modified_on': file.write_date,
                'created_by': file.create_uid.name,
                'company_id': file.company_id.name,
                'tags': tags
            }

            # Check security and append if allowed
            if not file.active_security or file.security_user_id.id == uid:
                result.append(file_info)

        total_count = file_model.search_count(domain)
        response = {
            'attachments': result,
            'total_count': total_count,
            'total_pages': math.ceil(total_count / page_limit),
            'per_page': page_limit,
            'page': page_number,
            'success': True
        }
        return response
