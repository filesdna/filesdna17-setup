import base64
import io
import zipfile
import xmlrpc
import odoo
import time
from odoo import http, fields, exceptions, _
from odoo.http import request, content_disposition
import tempfile
from odoo.tools.misc import str2bool
from urllib.parse import urlparse
from contextlib import closing
from odoo.addons.web.controllers.main import Database
from odoo.service.db import _create_empty_database
from odoo.tools import config
from odoo.exceptions import ValidationError
# try:
#     from addons.website_sale.controllers.main import WebsiteSale
# except:
#     from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.service import db
import os
import datetime
import logging

_logger = logging.getLogger(__name__)

from ... import saas_product


class saas_pro_inherit(saas_product.controller.main.saas_pro):

    #To Restore Databse From Website
    @http.route('/apps/restore_database', auth='public',type="json" ,website=True)
    def restore_database(self, **kw):
        try:
            _logger.info("\n\nrestore_database_id: {}\n\n".format(kw.get('db_id')))
            if kw.get('db_id') and kw.get('db_path'):
                tenant_id = request.env['tenant.database.list'].sudo().browse(int(kw.get('db_id')))
                backup_zip_name = kw.get('db_path')
                _logger.info("\nurl: {}\n\n".format(backup_zip_name))
                ICPSudo = request.env['ir.config_parameter'].sudo()
                # tenant_port = ICPSudo.search([('key', '=', 'odoorc_port')]).value or ''
                # tenant_ip = ICPSudo.search([('key', '=', 'bare_tenant_ip')]).value or ''
                # if not tenant_port or not tenant_ip:
                #     raise ValidationError(_("Please Provide Port And IP Fore Bare Tenant In Settings!"))
                # url = 'http://' + tenant_ip + ':' +tenant_port
                # url = 'http://' + tenant_id.tenant_url
                url = ICPSudo.search([('key', '=', 'brand_website')]).value or ''
                if not url:
                    raise ValidationError(_("Please Provide Brand Website In Settings!"))
                master_password = ICPSudo.search([('key', '=', 'tenant_conf_master_pwd')]).value or ''
                if not master_password:
                    raise ValidationError(_("Please Provide Master Password Of Tenant In Settings!"))
                with open(backup_zip_name, 'rb') as backup_file:
                    server = xmlrpc.client.ServerProxy(url + '/xmlrpc/db')
                    db_name = tenant_id.name
                    _logger.info("\nserverlist: {}\n\n".format(server.list()))
                    #To Drop Current Database
                    _logger.info("\n**************DB Drop Started************")
                    # dispatch_rpc('db','drop', [master_password, db_name])
                    server.drop(master_password, db_name)
                    _logger.info("\n**************Completed The DB Drop************")
                    # _logger.info("\nserverlist222: {}\n\n".format(server.list()))
                    #To Restore Database
                    _logger.info("\n**************DB Restore Started************")
                    server.restore(master_password, db_name, base64.b64encode(backup_file.read()).decode())
                    _logger.info("\n**************Completed The DB Restoration************")
        except Exception as e:
            raise exceptions.UserError(e)
        return True
    
        
    @http.route('/download/db_backup', auth='public', website=True)
    def _make_zip(self, **kw):
        """returns zip files for the Document Inspector and the portal.
        :return: a http response to download a zip file.
        """
        path = urlparse(kw['id'])
        name = os.path.basename(path.path)  # File name
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                with zipfile.ZipFile(kw['id'], 'r') as zip_ref:
                    listoffiles = zip_ref.namelist()
                    for attachment in listoffiles:
                        datas = base64.b64encode(zip_ref.read(attachment))
                        filename = attachment
                        doc_zip.writestr(filename, base64.b64decode(datas),
                                         compress_type=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipfile:
            _logger.exception("BadZipfile exception")
        content = stream.getvalue()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    @http.route('/apps/db_details', auth='public', website=True)
    def db_details(self, **kw):
        user = False
        if request.session.uid:
            user = request.session.uid
            user = request.env['res.users'].sudo().search([('id', '=', user)])

        tenant = request.env['tenant.database.list'].sudo().search([('id', '=', kw.get('id'))])
        # return json.dumps(tenant.id)
        registry = odoo.registry(tenant.name)
        users = []
        users_inactive = []
        with registry.cursor() as tenant_cr:
            tenant_env = odoo.api.Environment(tenant_cr, 1, {})
            main_tenant_user = tenant_env['res.users'].sudo().search([('tenant_user', '=', True)], limit=1)
            active_domain = []
            inactive_domain = [('active', '=', False)]

            if main_tenant_user:
                active_domain.append(('id', '>=', main_tenant_user.id))
                inactive_domain.append(('id', '>=', main_tenant_user.id))

            tenant_users = tenant_env['res.users'].sudo().search(active_domain)
            for item in tenant_users:
                if item.tenant_user:
                    users.append({'name': item.name, 'login': item.login, 'sub_user': True})
                else:
                    users.append({'name': item.name, 'login': item.login, 'sub_user': False})

            tenant_users = tenant_env['res.users'].sudo().search(inactive_domain)
            for item in tenant_users:
                users_inactive.append({'name': item.name, 'login': item.login, 'sub_user': False})
            AllzipFiles = []
            ###################################################################
            backup_store_path = request.env['db.backup'].sudo().search([])
            if backup_store_path and backup_store_path.folder:
                tenant_path = os.path.join(backup_store_path.folder, tenant.name)
                if os.path.exists(tenant_path):
                    for file in os.listdir(tenant_path):
                        filepath = os.path.join(tenant_path, file)
                        timestamp = os.stat(filepath).st_mtime
                        createtime = datetime.datetime.fromtimestamp(timestamp)
                        dictdata = {'file': file, 'download_path': filepath,
                                    'createdate': createtime}

                        AllzipFiles.append(dictdata)
            ###################################################################
        res = {
            'tenant': tenant,
            'users': users,
            'users_inactive': users_inactive,
            'db': tenant.name,
            'backup_files':False,
        }

        AllzipFilesList = sorted(AllzipFiles, key=lambda d: d['createdate'], reverse=True)

        if AllzipFilesList:
            files = {'backups': AllzipFilesList}
            res.update(files)
            res['backup_files'] = True
        return request.render('saas_product.saas_tenants', res)
