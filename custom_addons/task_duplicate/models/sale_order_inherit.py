from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def action_duplicate(self):
        print("inside action_duplicate")
        product_template_id = self.product_id.product_tmpl_id  # الحصول على قالب المنتج

        if not product_template_id:
            print("No product template found.")
            return

        print('product_template_id=', product_template_id.id)

        order_duplicate = self.env['sale.order.line'].create({
            'name': product_template_id.name,
            'product_id': self.product_id.id,  # استخدام معرف المنتج الحالي
            'order_id': self.order_id.id,  # استخدام self.order_id.id بدلاً من self.id
            'price_unit': self.price_unit,  # استخدام سعر الوحدة من السطر الحالي
            'product_uom_qty': self.product_uom_qty,  # استخدام الكمية من السطر الحالي
            'tax_id': [(6, 0, self.tax_id.ids)],  # استخدام ضرائب السطر الحالي
        })

        self.order_id.order_line = [(4, order_duplicate.id)]
        print('order_duplicate=', order_duplicate.name)