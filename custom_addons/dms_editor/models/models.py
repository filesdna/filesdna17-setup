# -*- coding: utf-8 -*-

from io import BytesIO
from odoo import models, fields, api
import requests
import base64
import json

class DmsEditorReact(models.Model):
    _inherit = 'dms.file'

    data_path = fields.Char(string= "Data Path",compute='_compute_data_path',
        compute_sudo=True,
        readonly=True,
        store=True)

    @api.depends("sha512_hash")
    def _compute_data_path(self):
        for record in self:
            record.data_path = f"document/{record.sha512_hash}"


    def action_edit(self):
        for record in self:
            record.ensure_one()
            action = record.env.ref('dms_editor.action_editor_page').read()[0]
            base_url = '/react/home'
            query_params = f"?data_path={record.data_path}-{record.current_time_seconds}"
            action['url'] = base_url + query_params
            return action     
 





