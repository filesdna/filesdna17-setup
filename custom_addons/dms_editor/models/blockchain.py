# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.addons.dms_editor.services.blockchain import BlockchainService

_logger = logging.getLogger(__name__)

class CreateBlockchain(models.Model):
    _inherit = 'res.users'

    bc_account = fields.Text(string='Blockchain Account')
    blockchain_uid = fields.Char(string='Blockchain ID')

    @api.model
    def create(self, values):
        result = super().create(values)
        try:
            request.env['user.verification'].sudo().create({'user_id':result.id})
            # Create Blockchain account
            blockchain = BlockchainService()
            bc_acc = blockchain.create_account_in_blockchain(result.blockchain_uid)
            if bc_acc:
                random_string = ''.join(random.choices("0123456789abcdefghiklmnopqrstuvwxyz", k=length))
                prefix = "filesdna|"
                result.write({'bc_account': bc_acc,'blockchain_uid':f"{prefix}{random_string}"})
                
            else:
                _logger.warning(f"Blockchain account creation failed for user {result.id}")
        except Exception as e:
            _logger.error(f"Error creating blockchain account for user {result.id}: {str(e)}")
        return result

