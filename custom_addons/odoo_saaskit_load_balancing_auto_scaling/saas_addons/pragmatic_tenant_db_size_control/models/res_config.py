from odoo import models, fields, api
import json
import re


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tenant_db_size = fields.Float(readonly=False,
                                    string="Default Tenant DB Size(GB)",
                                    default_model="res.company",
                                    default=5.0,
                                   )
    
    tenant_filestore_size = fields.Float(readonly=False,
                                           string="Default Tenant Filestore Size(GB)",
                                           default=5.0,
                                           )

    db_size_usage_product = fields.Many2one('product.product', readonly=False,
                                            help="This product will be used for invoicing related to extra database size usage",
                                            string="Extra DB Size Usage Product",
                                            config_parameter="db_size_usage_product")

    filestore_size_usage_product = fields.Many2one('product.product', readonly=False,
                                                   help="This product will be used for invoicing related to extra filestore size usage",
                                                   string="Extra Filestore Size Usage Product",
                                                   config_parameter="filestore_size_usage_product")

    filestore_path = fields.Char(readonly=False,
                                 default=".../.local/share/Odoo/filestore/",
                                string="Filestore Path",
                                config_parameter="filestore_path")

    flush_storage_history = fields.Integer(readonly=False, default=90,
                                            string="Flush Storage History Before(Days)",
                                            config_parameter="flush_storage_history")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        # print ("get values, resssss=======",res)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            tenant_db_size=ICPSudo.get_param('tenant_db_size'),
            tenant_filestore_size=ICPSudo.get_param('tenant_filestore_size'))
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.set_configs('tenant_db_size', self.tenant_db_size or 5.0)
        self.set_configs('tenant_filestore_size', self.tenant_filestore_size or 5.0)
        return res
class Rescompany(models.Model):
    _inherit = "res.company"

    default_db_size = fields.Char(string='Custom Module Path2',
                                  help="Set the path of Custom modules on Odoo server")
