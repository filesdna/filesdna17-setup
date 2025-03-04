from importlib.resources import path
from odoo import models, fields, api
from pathlib import Path

import logging
_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    web_configuration = fields.Selection([('apache', 'Apache'), ('nginx', 'NGINX')], default='apache',
                                         config_parameter="web_configuration")


class domain_masking(models.Model):
    _inherit = "domain.masking.details"

    @api.model
    def create_domain_masking_details(self, args):

        _logger.info("create domaing masking details.>>>>>>>{}".format(args))
        _logger.info(
            "create domaing masking details.>>>>>>>{}".format(args[4]))
        _logger.info("create domaing masking details.>>>>>>>{}".format(
            Path(args[5]).name))
        _logger.info("create domaing masking details.>>>>>>>{}".format(
            args[5].split("\\")[-1]))
        _logger.info("create domaing masking details.>>>>>>>{}".format(
            args[6].split("\\")[-1]))
        _logger.info("create domaing masking details.>>>>>>>{}".format(
            args[7].split("\\")[-1]))

        domain_mask_id = self.env['domain.masking.details'].sudo().create({
            'client_domain': args[0],
            'client_ssl1_filename': args[5].split("\\")[-1],
            'client_ssl2_filename': args[6].split("\\")[-1],
            'client_ssl3_filename': args[7].split("\\")[-1],
            'client_ssl1': args[1],
            'client_ssl2': args[2],
            'client_ssl3': args[3],
            'domain_type': 'https',
            'tenant_db_management': int(args[4]),
        })
        domain_mask_id.action_set_client_domain()
        domain_mask_id.tenant_db_management.action_restart_apache()
        return True
