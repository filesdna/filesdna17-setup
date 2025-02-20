'''
Created on Dec 3, 2019

@author: Zuhair Hammadi
'''
from odoo import models, api
import json

class FinReportRendering(models.AbstractModel):
    _name = 'report.oi_financial_report.report_oi_fin_report'
    _description = _name
    
    @api.model
    def _get_report_values(self, docids, data=None):  # @UnusedVariable
        data = data if data is not None else {}
        report = self.env['oi_fin.report'].browse(data.get('active_id'))
        return report.data and json.loads(report.data) or {}