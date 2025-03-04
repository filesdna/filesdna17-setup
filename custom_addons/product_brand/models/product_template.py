from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)




class ProductTempBrand(models.Model):

    _inherit = 'product.template'

    brand_id = fields.Many2one(comodel_name='product.template.brand', string='Brand')
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )

    def genertate_variant_code(self):
        for template in self:
            first_string_of_name = template.name.split()
            if len(first_string_of_name) <= 1:
                first_string_of_name = template.name.split()[0]
                for variant in template.product_variant_ids:
                    variant_values = "-".join(variant.product_template_variant_value_ids.mapped('name'))  
                    internal_ref = f'{first_string_of_name}-{variant_values}'  
                    variant.default_code = internal_ref 
            elif len(first_string_of_name) == 2:
                first_string_of_name = template.name.split()[1]
                for variant in template.product_variant_ids:
                    variant_values = "-".join(variant.product_template_variant_value_ids.mapped('name'))  
                    internal_ref = f'{first_string_of_name}-{variant_values}'  
                    variant.default_code = internal_ref
            else: 
                first_string_of_name = template.name.split()[1]
                second_string_of_name = template.name.split()[2]
                for variant in template.product_variant_ids:
                    variant_values = "-".join(variant.product_template_variant_value_ids.mapped('name'))  
                    internal_ref = f'{first_string_of_name}-{second_string_of_name}-{variant_values}'  
                    variant.default_code = internal_ref 

    def _create_variant_ids(self):
        res = super(ProductTempBrand, self)._create_variant_ids()
        for template in self:
            first_string_of_name = template.name.split()
            if len(first_string_of_name) <= 1:
                first_string_of_name = template.name.split()[0]
                for variant in template.product_variant_ids:
                    variant_values = "-".join(variant.product_template_variant_value_ids.mapped('name'))  
                    internal_ref = f'{first_string_of_name}-{variant_values}'  
                    variant.default_code = internal_ref 
            elif len(first_string_of_name) == 2:
                first_string_of_name = template.name.split()[1]
                for variant in template.product_variant_ids:
                    variant_values = "-".join(variant.product_template_variant_value_ids.mapped('name'))  
                    internal_ref = f'{first_string_of_name}-{variant_values}'  
                    variant.default_code = internal_ref
            else: 
                first_string_of_name = template.name.split()[1]
                second_string_of_name = template.name.split()[2]
                for variant in template.product_variant_ids:
                    variant_values = "-".join(variant.product_template_variant_value_ids.mapped('name'))  
                    internal_ref = f'{first_string_of_name}-{second_string_of_name}-{variant_values}'  
                    variant.default_code = internal_ref 
        return res
    

class ProductcompanyDefault(models.Model):

    _inherit = 'product.template'

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    

    