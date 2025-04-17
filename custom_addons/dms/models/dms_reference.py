from odoo import api, fields, models
from datetime import datetime


class Reference(models.Model):
    _name = "dms.reference"
    _description = "Reference"

    name = fields.Char(required=True)
    start = fields.Integer()
    reference_line = fields.One2many('dms.reference.line', 'reference_id', order="sequence")
    reference_name = fields.Char(compute='_compute_reference_name')
    reference_name_without_start = fields.Char(compute='_compute_reference_name_without_start')
    is_year = fields.Boolean()
    is_default = fields.Boolean()
    year_line_id = fields.Many2one('dms.reference.line', string="Year Line")
    doc_param_year_id = fields.Many2one('document.parameters',
                                   string="Document Parameter")
    year_record_id = fields.Many2one('document.parameters.line',
                                     string="Year Record")
    #-----------------------------------------------------------------------
    month_line_id = fields.Many2one('dms.reference.line', string="Year Line")
    doc_param_month_id = fields.Many2one('document.parameters',
                                   string="Document Parameter")
    month_record_id = fields.Many2one('document.parameters.line',
                                     string="Year Record")

    @api.onchange('reference_line.doc_parm_line', 'reference_line.separator')
    def _compute_reference_name(self):
        for rec in self:
            reference_lines = rec.reference_line.sorted(key=lambda r: r.sequence)
            names = []
            for line in reference_lines:
                if line.doc_parm_line:
                    names.append(str(line.doc_parm_line.reference_value))
                    if line.separator:
                        names.append(line.separator)

            if rec.start is not None:
                names.append(str(rec.start))
            rec.reference_name = ''.join(names).rstrip(', ')

    @api.onchange('reference_line.doc_parm_line', 'reference_line.separator')
    def _compute_reference_name_without_start(self):
        print('reference_name_without_start')
        for rec in self:
            reference_lines = rec.reference_line.sorted(key=lambda r: r.sequence)
            names = []
            for line in reference_lines:
                if line.doc_parm_line:
                    names.append(str(line.doc_parm_line.reference_value))
                    if line.separator:
                        names.append(line.separator)
            rec.reference_name_without_start = ''.join(names).rstrip(', ')

    @api.onchange('add_year')
    def add_year(self):
        for rec in self:
            # Create Year record
            doc_param_year = self.env['document.parameters'].create({
                'name': 'Year',
                'active': False,
            })
            current_year = datetime.now().year
            year_record = self.env['document.parameters.line'].create({
                'document_parameters': doc_param_year.id,
                'name': str(current_year),
                'reference_value': current_year % 100
            })

            # Create Month record
            doc_param_month = self.env['document.parameters'].create({
                'name': 'Month',
                'active': False,
            })
            current_month = datetime.now().month
            month_record = self.env['document.parameters.line'].create({
                'document_parameters': doc_param_month.id,
                'name': str(current_month),
                'reference_value': current_month
            })

            # Create record in dms.reference.line and store its ID
            year_line = self.env['dms.reference.line'].create({
                'reference_id': rec.id,
                'sequence': 1,
                'doc_parm': doc_param_year.id,
                'doc_parm_line': year_record.id,
                'separator': '-',
            })

            month_line = self.env['dms.reference.line'].create({
                'reference_id': rec.id,
                'sequence': 2,
                'doc_parm': doc_param_month.id,
                'doc_parm_line': month_record.id,
                'separator': '-',
            })

            # Store the IDs
            rec.year_line_id = year_line.id  # Store the ID of the record in dms.reference.line for Year
            rec.doc_param_year_id = doc_param_year.id  # Store the ID of the Year record in document.parameters
            rec.year_record_id = year_record.id  # Store the ID of the Year record in document.parameters.line

            rec.month_line_id = month_line.id  # Store the ID of the record in dms.reference.line for Month
            rec.doc_param_month_id = doc_param_month.id  # Store the ID of the Month record in document.parameters
            rec.month_record_id = month_record.id  # Store the ID of the Month record in document.parameters.line

            rec.is_year = True

    def remove_year(self):
        for rec in self:
            # Remove Year related records
            if rec.year_line_id and rec.month_line_id:
                rec.year_line_id.unlink()
                rec.year_line_id = False
                rec.month_line_id.unlink()
                rec.month_line_id = False

            if rec.year_record_id and rec.month_record_id:
                rec.year_record_id.unlink()
                rec.year_record_id = False
                rec.month_record_id.unlink()
                rec.month_record_id = False

            if rec.doc_param_year_id and rec.doc_param_month_id:
                rec.doc_param_year_id.unlink()
                rec.doc_param_year_id = False
                rec.doc_param_month_id.unlink()
                rec.doc_param_month_id = False

            rec.is_year = False

    @api.model
    def create(self, vals):
        # Create the record
        record = super(Reference, self).create(vals)
        if record.is_default:
            record.add_year()
        return record

class Referenceline(models.Model):
    _name = "dms.reference.line"
    _description = "Reference"

    reference_id = fields.Many2one('dms.reference')
    sequence = fields.Integer()
    separator = fields.Selection([
        ('-', '-'),
        ('/', '/'),
    ])
    doc_parm = fields.Many2one('document.parameters')
    doc_parm_line = fields.Many2one('document.parameters.line', domain="[('document_parameters', '=', doc_parm)]")
    reference_value = fields.Char(related='doc_parm_line.reference_value')
