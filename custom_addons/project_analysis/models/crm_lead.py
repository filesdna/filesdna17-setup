from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_create_new_quotation(self):
        """Redirects to the Quotation form with prefilled values from CRM Lead."""
        return {
            'name': 'New Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'view_id': self.env.ref("sale.view_order_form").id,  # Ensure the correct form is used
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,  # Link it to the CRM Lead
                'default_opportunity_id': self.id,
                'default_state': 'draft'  # Ensure new records start as "Quotation"
            },
        }
