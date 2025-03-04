# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class CaseSubMatterCreate(models.TransientModel):
    
    _name = 'case.sub.matter.create'
    _description = """Case Sub Matter Create"""


    open_date = fields.Date(string="Open Date")
    close_date = fields.Date(string="Expected Close Date")

    @api.constrains('open_date', 'close_date')
    def _check_law_time_period(self):
        for record in self:
            if record.close_date and record.open_date and record.close_date < record.open_date:
                raise ValidationError("Please ensure the case expected close date is greater than the open date")

    def case_matter_details(self):
        case_id = self.env['case.matter'].browse(self._context.get('active_id'))
        data = {
            'case_matter': case_id.case_matter,
            'sub_case_id': case_id.id,
            'customer_id': case_id.customer_id.id,
            'matter_category_id': case_id.matter_category_id.id,
            'matter_sub_category_id': case_id.matter_sub_category_id.id,
            'open_date': self.open_date,
            'close_date': self.close_date,
            'case_state_id':case_id.state_id.id,
            'case_country_id':case_id.country_id.id,
            'referral_id':case_id.referral_id.id
        }
        case_id.locked = True
        case_matter_id = self.env['case.matter'].create(data)
        # crm_lead_id.case_matter_id = case_matter_id.id
        case_matter_id.customer_details()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Case'),
            'res_model': 'case.matter',
            'res_id': case_matter_id.id,
            'view_mode': 'form',
            'target': 'current'
        }



    def set_draft(self):
        case_id = self.env['case.matter'].browse(self._context.get('active_id'))
        case_id.case_re_open()