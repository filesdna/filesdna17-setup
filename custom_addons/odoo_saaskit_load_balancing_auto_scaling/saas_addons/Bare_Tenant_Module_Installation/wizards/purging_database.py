from odoo import models, fields, exceptions, _, api
from odoo.exceptions import UserError
import paramiko
from contextlib import closing
import odoo
from odoo.service.db import exp_drop
import logging
_logger = logging.getLogger(__name__)


class PurgeDatabase(models.TransientModel):
    _name = 'purge.database'
    _description = "Purge Database"

    # delete_me = fields.Char(string="Delete Me")
    tenant_id = fields.Many2one('tenant.database.list', string='Tenant')

    @api.model
    def default_get(self, fields_list):
        default_vals = super(PurgeDatabase, self).default_get(fields_list)
        tenant = self.env['tenant.database.list'].browse(int(self.env.context.get('active_id')))

        default_vals.update({'tenant_id':tenant.id})       
        return default_vals

    # def database_que_job(self):
    #     if self.delete_me == "DELETE ME":
    #         try:
    #             self.with_delay().delete_database()
    #             _logger.info("database queue job >>>>>>>>>>")
    #             view_id = self.env.ref('Bare_Tenant_Module_Installation.purge_database_reminder_form_view').id
    #             _logger.info("database queue job aftereee>>>>>>>>>>")
    #             return {'type': 'ir.actions.act_window',
    #                     'name': _('Reminder'),
    #                     'res_model': 'purge.database',
    #                     'target': 'new',
    #                     'view_mode': 'form',
    #                     'views': [[view_id, 'form']],
    #             }
    #         except Exception as e:
    #             _logger.info("exception >>>>>>>>>>>>>>>{}".format(e))
    #             # self.delete_database()
    #     else:
    #         raise UserError(_("Please insert correct input.Text is case sensitive."))

    def purge_tenant_database(self):
        _logger.info("active id >>>>>>{}".format(self.env.context))
        try:
            tenant_db = self.tenant_id
            agreement_obj = self.env['sale.recurring.orders.agreement'].sudo()
            db_name = tenant_db.name

            # Deactivate agreements
            agreement_ids = agreement_obj.search([('order_line.order_id.instance_name', '=', str(db_name))])
            agreement_ids.write({'active': False})
            
            #Cancel Related Sale Order
            if tenant_db.sale_order_ref:
                tenant_db.sale_order_ref._action_cancel()  
            
            # Deactivate Tenant DB List
            stage_ids = self.env['tenant.database.stage'].search([('is_purge', '=', True)])
            tenant_db.write({'stage_id': stage_ids[0].id if stage_ids else False})
                
            #Base Function To Drop Database
            # exp_drop(db_name)

        except Exception as e:
            _logger.info("Exception >>>>>>>>>>>{}".format(e))
        _logger.info("last print >>>>>>>>>>>>")