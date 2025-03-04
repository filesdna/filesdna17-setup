# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class CustodyProperty(models.Model):
    """
        Hr property creation model.
    """
    _name = 'custody.property'
    _description = 'Custody Property'

    name = fields.Char(string='Property Name', required=True,
                       help='Enter the name of the custody property')
    image = fields.Image(string="Image",
                         help="This field holds the image used for "
                              "this provider, limited to 1024x1024px")
    image_medium = fields.Binary(
        "Medium-sized image", attachment=True,
        help="Medium-sized image of this provider. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized image", attachment=True,
        help="Small-sized image of this provider. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    desc = fields.Html(string='Description',
                       help='A detailed description of the item.')
    company_id = fields.Many2one('res.company', 'Company',
                                 help='The company associated with '
                                      'this record.',
                                 default=lambda self: self.env.user.company_id)
    property_selection = fields.Selection([('empty', 'No Connection'),
                                           ('product', 'Products')],
                                          default='empty',
                                          string='Property From',
                                          help="Select the property")

    archive = fields.Boolean()

    product_template_id = fields.Many2one('product.template', domain="[('is_custody', '=', True)]")
    vendor_purchase = fields.Many2one('product.supplierinfo', domain="[('product_tmpl_id', '=', product_template_id)]")
    product_purchase_price = fields.Float(related='vendor_purchase.price', store=True)
    stock_lot = fields.Many2one('stock.lot',  domain="[('product_id', '=', product_template_id)]")
    hr_custody = fields.Many2one('hr.custody')
    employee_custody = fields.Many2one(related='hr_custody.employee_id')
    state = fields.Selection([
        ('new', 'New'),
        ('good_conditions', 'Good Conditions'),
        ('scrap', 'Scrap'),
    ], default='new')

    @api.onchange('product_template_id', 'stock_lot')
    def onchange_product(self):
        """The function is used to
            change product Automatic
            fill name field"""
        if self.product_template_id and self.stock_lot:
            self.name = f"{self.product_template_id.name} - {self.stock_lot.name}"
        elif self.product_template_id:
            self.name = self.product_template_id.name
        elif self.stock_lot:
            self.name = self.stock_lot.name

    def action_scrap(self):
        print('action_scrap')
        self.archive = True
        self.state = 'scrap'

    def action_return(self):
        print('action_return')
        self.archive = False
        self.state = 'new'

