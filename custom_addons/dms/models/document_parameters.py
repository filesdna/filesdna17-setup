import logging

from odoo import api, fields, models


class DocumentParameters(models.Model):
    _name = "document.parameters"
    _description = "Document Parameters"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    document_parameters_line = fields.One2many("document.parameters.line", 'document_parameters', required=True)
    required = fields.Boolean(default=False)
    # file_id = fields.Many2one('dms.file')

    @api.model
    def action_active(self):
        for rec in self:
            rec.active = True  # Correctly set the active field to True

    @api.model
    def create(self, vals):
        record = super(DocumentParameters, self).create(vals)
        dms_files = self.env['dms.file'].search([])
        if dms_files:
            for dms_file in dms_files:
                print('dms_file_id=', dms_file.id)
                print('record_id=', record.id)
                create_doc_parm_file = self.env['dms.link.document.parameter.line'].create({
                    'parameter_id': record.id,
                    'file_id': dms_file.id,
                })
                print('create_doc_parm_file=', create_doc_parm_file)
        else:
            print('No dms.file records found.')

        access_id = self.env['dms.access.group'].search([])
        if access_id:
            for access in access_id:
                print('access=', access.id)
                create_doc_parm_file_access = self.env['dms.link.document.parameter.line'].create({
                    'parameter_id': record.id,
                    'access_id': access.id,
                })
                print('create_doc_parm_file_access=', create_doc_parm_file_access)
        else:
            print('No access records found.')
        return record

    def action_required(self):
        print('action_required')
        self.required = True

    def action_not_required(self):
        print('action_not_required')
        self.required = False

    def unlink(self):
        for record in self:
            self.env['dms.link.document.parameter.line'].search([
                ('parameter_id', '=', record.id)
            ]).unlink()
            record.document_parameters_line.unlink()
        return super(DocumentParameters, self).unlink()


class DocumentParametersLine(models.Model):
    _name = "document.parameters.line"
    _description = "Document Parameters"

    name = fields.Char(required=True)
    sequence = fields.Integer()
    reference_value = fields.Char(required=True)
    # access_id = fields.Many2one('dms.access.group')

    document_parameters = fields.Many2one('document.parameters')
    document_parameters_line = fields.Many2one('document.parameters.line',
                                               domain="[('document_parameters', '=', document_parameters)]",
                                               )
    # document_id = fields.Many2one('dms.file')

    active_doc = fields.Boolean(related='document_parameters.active')


class DMSDocumentParameter(models.Model):
    _name = "dms.link.document.parameter.line"
    _description = "Link Document Parameters"

    file_id = fields.Many2one('dms.file', string="Document", ondelete="cascade")
    access_id = fields.Many2one('dms.access.group', string="Access Group")
    advance_id = fields.Many2one('advance.search', string="Advance Search")
    parameter_id = fields.Many2one('document.parameters', string="Parameter", store=True)
    selected_value_id = fields.Many2one('document.parameters.line', string="Selected Value",
                                        domain="[('document_parameters', '=', parameter_id)]")
    reference_value = fields.Char(related='selected_value_id.reference_value')
    active = fields.Boolean(related='parameter_id.active')

    selected_value_ids = fields.Many2many('document.parameters.line', string="Selected Value",
                                          domain="[('document_parameters', '=', parameter_id)]")
    reference_value_many = fields.Text(compute='_compute_reference_value_many', string="Reference Values")

    @api.depends('selected_value_ids.reference_value')
    def _compute_reference_value_many(self):
        for record in self:
            reference_values = record.selected_value_ids.mapped('reference_value')
            record.reference_value_many = ', '.join(reference_values)
