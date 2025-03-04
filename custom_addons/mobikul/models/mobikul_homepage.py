# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################
import logging
_logger = logging.getLogger(__name__)
from odoo import models,fields,api


class MobikulHomepage(models.Model):
    _name = "mobikul.homepage"
    _description = "Mobikul Homepage"
    _order = "sequence"

    name = fields.Char("Name",required=True, translate=True)
    sequence = fields.Integer(default=10, help='Display order')
    type = fields.Selection([
        ('banner', 'Banner'),
        ('slider', 'Slider'),
        ('featured_category', 'Featured Category')],
        string='Type', required=True,
        default='banner')
    banner_ids = fields.One2many("mobikul.banners", 'homepage_id', string='Banners')
    slider_ids = fields.One2many("mobikul.product.slider", 'homepage_id', string='Sliders')
    featured_category_ids = fields.Many2many("mobikul.category", string='Featured Category')
    featured_category_view = fields.Selection([
        ('circle', 'Circle'),
        ('rounded_square', 'Rounded Square'),
        ('square', 'Square'),],
        string='Featured Category View', required=True,
        default='circle',
        help="Set Featured Category View Type for your Mobikul App.")


class MobikulHomepageConfiguration(models.Model):
    _name = "mobikul.homepage.configuration"
    _description = "Mobikul Homepage Configuration"

    active = fields.Boolean(default=True)
    name = fields.Char("Name",required=True, translate=True)
    homepage_ids = fields.Many2many("mobikul.homepage", string="Homepage Data")

