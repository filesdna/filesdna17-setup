# -*- coding: utf-8 -*-
#################################################################################
# Author      : AxisTechnolabs.com
# Copyright(c): 2011-Axistechnolabs.com.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api


class appointment_source(models.Model):
    _name = 'appointment.source'
    _description = 'appointment_source'

    name = fields.Char(string='Source',required=True)