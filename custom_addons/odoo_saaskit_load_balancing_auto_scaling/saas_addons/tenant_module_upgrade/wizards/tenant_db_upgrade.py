from numpy import recfromcsv
from odoo import fields, api, models, _
from odoo import SUPERUSER_ID, api
from odoo import sql_db, _

import odoo
from contextlib import closing

import logging

_logger = logging.getLogger(__name__)



class TenantDbUpgrade(models.TransientModel):
    _name = 'tenant.db.upgrade'
    _description = 'Tenant Database Upgrade'

    tenant_db = fields.Many2many('tenant.database.list', string='Tenant DB')
    installed_modules = fields.One2many("installed.tenant.module", 'tenant_module_id',
                                        string="Installed Modules")
    db_list = []

    def upgrade(self):
        for db in self.tenant_db:
            database_name = db.name
            for mod in self.installed_modules:
                if mod.upgrade_bool:
                    registry = odoo.registry(database_name)
                    with closing(registry.cursor()) as cr:
                        env = api.Environment(cr, SUPERUSER_ID, {})
                        module_name = env['ir.module.module'].search(
                            [('name', '=', mod.technical_name), ('state', '=', 'installed')])
                        module_name.button_immediate_upgrade()
                        if mod.technical_name == "openerp_saas_tenant":
                            try:
                                gid_sql = "select id from res_groups where name = 'Psuedo Admin'"
                                env.cr.execute(gid_sql)
                                gid_vals = env.cr.fetchall()
                                for record in gid_vals:
                                    _logger.info("fetchall >>>>>>>{}".format(record))

                                    sql = """DELETE
                                    FROM ir_ui_menu_group_rel 
                                        WHERE gid = %s
                                        """ % (record)
                                    env.cr.execute(sql)
                            except Exception as e:
                                _logger.info("removing pseudo group not working!!!")
    def load_modules(self):
        module_list_1 = []
        module_list_2 = []
        for db in self.tenant_db:
            db_name = db.name
            registry = odoo.registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                installed_apps = env['ir.module.module'].search(
                    [('state', '=', 'installed')]) #, ('application', '=', True)
                id = self.id
                for module in installed_apps:
                    module_list_1.append((0, 0, {'tenant_module_id': id,
                                                 'module_name': module.shortdesc,
                                                 'technical_name': module.name,
                                                 'status': module.state
                                                 }))
        for module in module_list_1:
            if module not in module_list_2:
                module_list_2.append(module)
        self.write({'installed_modules': module_list_2})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tenant.db.upgrade',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }


class InstalledTenantModules(models.TransientModel):
    _name = 'installed.tenant.module'
    _description = 'Tenant Database Installed Modules'

    tenant_module_id = fields.Many2one('tenant.db.upgrade', string="module Id")
    upgrade_bool = fields.Boolean(default=False, string="Check", store=True)
    module_name = fields.Char('Module Name')
    technical_name = fields.Char('Module Technical Name')
    status = fields.Selection([('installed', 'Installed'),
                               ('uninstalled', 'Uninstalled'),
                               ('uninstallable', 'Uninstallable'),
                               ('to upgrade', 'To be Upgrade'),
                               ('to remove', 'To be Remove'),
                               ('to install', 'To be Install')])
