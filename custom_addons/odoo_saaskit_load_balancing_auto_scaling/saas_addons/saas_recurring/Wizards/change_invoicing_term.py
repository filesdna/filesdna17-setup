from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ChangeInvoicingTermWizard(models.TransientModel):
    _name = "change.invoicing.term.wizard"
    _description = "To compute values according to invoice policy after changing invoice term"

    invoice_term_id = fields.Many2one('recurring.term', 'Invoicing Term', readonly=False, required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ChangeInvoicingTermWizard, self).default_get(fields_list)
        # print('Wizards :\n\n    {}\n\n {} '.format(self, self._context))
        # current_obj = self.env['sale.recurring.orders.agreement'].sudo().browse(int(self._context.get('active_id')))
        # print('res :\n\n    {}\n\n {} {}'.format(res, current_obj, current_obj.invoice_term_id))
        # self.write({'invoice_term_id': int(current_obj.invoice_term_id.id)})

        return res


    def change_invoicing_term(self):
        current_obj = self.env['sale.recurring.orders.agreement'].sudo().browse(int(self._context.get('active_id')))

        if self.invoice_term_id.id == current_obj.invoice_term_id.id:
            raise UserError('Selected Invoicing Term is already their, Please select another one !')
        tenant = self.env['tenant.database.list'].sudo().search([('name', '=', current_obj.instance_name)])

        if tenant and tenant.sale_order_ref:
            term_type = self.invoice_term_id.name
            months_to_add = 0

            if term_type == 'Monthly': months_to_add = 1
            if term_type == 'Yearly': months_to_add = 12

            if months_to_add:
                new_exp_date = str(
                    datetime.strptime(str(tenant.exp_date), '%Y-%m-%d') + relativedelta(
                        months=+months_to_add))[:10]

                tenant.write({'exp_date': new_exp_date})
            so =  tenant.sale_order_ref
            so.write({'invoice_term_id': int(self.invoice_term_id.id)})
            current_obj.write({'invoice_term_id': int(self.invoice_term_id.id)})