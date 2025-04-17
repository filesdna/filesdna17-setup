#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2018-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################


from odoo import api, models, fields, exceptions

import logging
_logger = logging.getLogger(__name__)


class EmailVerificationConfig(models.TransientModel):
	_name = 'email.verification.config'
	_inherit = 'res.config.settings'
	_description = 'Email Verification Config'

	@api.constrains('token_validity')
	def positive_validity(self):
		if self.token_validity and self.token_validity<0:
			raise exceptions.UserError('Validity should be positive.')
			

	token_validity = fields.Integer(
		string='Token Validity In Days',
		related="website_id.token_validity",
		help="Validity of the token in days sent in email. If validity is 0 it means infinite.",
		readonly=False
  	)
	restrict_unverified_users = fields.Boolean(
		string='Restrict Unverified Users From Checkout',
		related="website_id.restrict_unverified_users",
		help="If enabled unverified users can not proceed to checkout untill they verify their emails",
		readonly=False,
	)
