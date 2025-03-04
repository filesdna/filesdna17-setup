# -*- coding: utf-8 -*-
from odoo import api, fields, models
import psycopg2
from odoo import exceptions
from odoo.exceptions import UserError, ValidationError
import odoo
import datetime
from odoo.tools.translate import _
from odoo import SUPERUSER_ID, api
from odoo import sql_db, _
from odoo.tools import config
from odoo.service import db
import xmlrpc
from datetime import datetime
from contextlib import closing
import traceback
import logging

ADMINUSER_ID = 2
_logger = logging.getLogger(__name__)


class IncreaseNoOfUsersWizard(models.TransientModel):
    """ Manually Increase the no of users in database from saas kit"""
    _name = 'increase.tenant.users.wizard'
    _description = 'Increase No of Users in Tenant Database'

    default_no_of_users = fields.Integer('Default No of Users', readonly=True, required=True)
    updated_no_of_users = fields.Integer('Update No of Users', required=True)

    def update_no_of_tenant_users(self):
        '''
            This function will update all the no of users field which are related to tenant database
        '''
        try:
            tenant = self.env[self._context.get('active_model')].sudo().browse(int(self._context.get('active_id')))
            if tenant and int(self.updated_no_of_users) > 0:
                ############################################
                # Updating user size In tenant form in saas kit
                _logger.info('==================== Updating user size In tenant form in saas kit ')
                ############################################
                tenant.write({
                    'no_of_users': int(self.updated_no_of_users),
                })

                ############################################
                # Updating user size in agreement on saas kit
                _logger.info('==================== Updating user size in agreement on saas kit ')
                ############################################
                tenant_agreement = self.env['sale.recurring.orders.agreement'].sudo().search([('instance_name', '=', tenant.name)])
                if tenant_agreement:
                    tenant_agreement.write({
                        'current_users': int(self.updated_no_of_users)
                    })

                ############################################
                # Updating user size Forcely on tenant database service
                _logger.info('==================== Updating user size Forcely on tenant database service ')
                ############################################
                config_path = self.env['ir.config_parameter'].sudo()
                brand_website = config_path.search([('key', '=', 'brand_website')]).value
                brand_admin = tenant.super_user_login
                brand_pwd = tenant.super_user_pwd

                dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
                uid_dst = common.authenticate(tenant.name, brand_admin, brand_pwd, {})
                dest_model.execute_kw(tenant.name, uid_dst, brand_pwd, 'saas.service', 'write',
                                      [1, {
                                          'user_count': tenant.no_of_users,
                                      }])
            else:
                raise UserError(_('Number Of User Should Be Greater Than Zero!!'))
        except Exception as e:
            _logger.info('Exception while updating no of users : {} '.format(e))
            raise UserError('Error : {} '.format(e))

    # @api.onchange('updated_no_of_users')
    # def restrict_increase_less_no_of_users(self):
    #     '''
    #         This function will restrict to enter less no of users than default users in tenant
    #     '''
    #     if self.updated_no_of_users < self.default_no_of_users:
    #         self.write({
    #            'updated_no_of_users':self.default_no_of_users
    #         })
    #         raise UserError('Please enter user count greater than default users')
    #
