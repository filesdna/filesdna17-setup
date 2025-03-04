from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class TenantDatabaseList(models.Model):
    _inherit = "tenant.database.list"

    tenant_master_password = fields.Char(string="Tenant Master Password", default='admin')

