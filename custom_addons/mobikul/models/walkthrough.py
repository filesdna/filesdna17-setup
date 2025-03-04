# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################
from odoo import fields, models
import logging
_logger = logging.getLogger(__name__)

class MobikulWalkThough(models.Model):
    _name = 'mobikul.walkthrough'
    _description = 'Mobikul WAlkthrough Message'

    name = fields.Char('Title', required=True)
    image = fields.Binary('Image', attachment=True,help="Recommended Image Aspect Ratio: 1:2 And Size: 1374px * 1080px (Height x Width)")
    color_code = fields.Char('Color Code')
    sequence = fields.Integer(default=1, help='Display order', required=True)
    status = fields.Selection([
        ('enable', 'Enable'),
        ('disable', 'Disable')],
        string='Status', required=True,
        default='enable')
    description = fields.Text('Description')


    def toggle_walkthrough_status(self):
        self.ensure_one()
        if self.status == 'enable':
            self.status = 'disable'
        else:
            self.status = 'enable'
        return True
