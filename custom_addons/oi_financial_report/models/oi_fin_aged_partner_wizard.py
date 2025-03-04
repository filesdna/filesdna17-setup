'''
Created on Oct 21, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api, _
from collections import defaultdict

class AgedPartner(models.TransientModel):
    _name = 'oi_fin.aged.partner.wizard'
    _description = 'Aged Partner Wizard'
    _inherit = 'oi_fin.aged.partner'
    
    template_id = fields.Many2one('oi_fin.aged.partner.template')
    line_ids = fields.One2many('oi_fin.aged.partner.wizard.line', 'wizard_id')
    date = fields.Date(required = True, default = fields.Date.today)
    company_id = fields.Many2one('res.company', required = True, default = lambda self : self.env.company)
    
    currency_id = fields.Many2one(required = True, default = lambda self : self.env.company.currency_id)
    currency_rate = fields.Float(default = 1, digits=(12, 6))     
    
    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, 'Aged Partner Balance'))
        return res
    
    @api.onchange('currency_id', 'date', 'company_id')
    def _onchange_currency_id(self):
        self.currency_rate = self.currency_id.with_context(date = self.date, company_id = self.company_id.id).rate    
    
    @api.onchange('template_id')
    def _onchage_template_id(self):
        if self.template_id:
            data, = self.template_id.copy_data()
            for name, value in data.items():
                if name in self._fields:
                    field = self._fields[name]
                    if field.type in ['one2many', 'many2many']:
                        self[name] = False
                    if field.required and not value:
                        continue                        
                    self[name] = value
    
    def _get_data(self):
        res = {
            'columns' : [],
            'accounts' : []
            }
        
        for line in self.line_ids:
            name = '%s (%s)' % (line.name, self.currency_id.name)                
            res['columns'].append(name)        
        
        account_ids = self.account_ids
        if not account_ids:
            account_type = self.type and [self.type] or ['asset_receivable', 'liability_payable']
            account_ids = self.env['account.account'].search([('account_type', 'in', account_type)])
        domain = [('account_id', 'in', account_ids.ids), ('reconciled', '=', False), ('company_id', '=', self.company_id.id)]
        if self.partner_tag_ids:
            domain.append(('partner_id.category_id', 'in', self.partner_tag_ids.ids))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        groups_account = self.env['account.move.line'].read_group(domain, ['account_id'], ['account_id'])
        for account_data in groups_account:            
            vals = {
                'account_id' : self.env['account.account'].browse(account_data['account_id'][0]),
                'partners' : [],
                'totals' : defaultdict(float)
                }
            groups_partner = self.env['account.move.line'].read_group(account_data['__domain'], ['partner_id'], ['partner_id'])
            for partner_data in groups_partner:
                partner_id =partner_data['partner_id'] and partner_data['partner_id'][0] or False
                partner_vals = {
                    'partner_id' : self.env['res.partner'].browse(partner_id),
                    'total' : [],
                    }
                move_line_ids = self.env['account.move.line'].search(partner_data['__domain'], order = 'date_maturity,id')
                move_line_vals = defaultdict(dict)
                for col_index, col in enumerate(self.line_ids):
                    total = 0
                    for move_line in move_line_ids:
                        if move_line.move_id.state !='posted':
                            continue
                        
                        if move_line.date_maturity:
                            days = (self.date - move_line.date_maturity ).days 
                        else:
                            days = 0 

                        value = col._check_condition(days) and move_line.amount_residual or float()
                        value = self.currency_id.round(value * self.currency_rate)                        
                        move_line_vals[move_line]['move_line'] = move_line
                        move_line_vals[move_line][col_index] = value
                        total += value
                        vals['totals'][col_index] += value 
                    partner_vals['total'].append(total)     
                partner_vals['details'] = sorted(move_line_vals.values(), key = lambda item : (item['move_line'].date_maturity or item['move_line'].date, item['move_line'].id))                                                                                  
                vals['partners'].append(partner_vals)
            res['accounts'].append(vals)
        return res
            
    
    def action_excel(self):
        data = self._get_data()
        pdf = self._context.get('pdf', False)
        html = self._context.get('html', False)        
        header = [_('Partner'), _('Partner Reference'), _('Reference'), _('Due Date')]
        extra = []
        
        def get_display(names):
            if not names:
                return 
            names = filter(lambda i : isinstance(i, str), names)
            return ','.join(names)
        
        if self.show_payment_terms:
            header.append(_('Payment Terms'))
            extra.append(lambda line : line.invoice_id.payment_term_id.display_name)
            
            
        if self.show_salesperson_name:
            header.append(_('Salesperson'))
            extra.append(lambda line : line.partner_id.user_id.display_name)
            
        if self.show_salesperson_reference:
            header.append(_('Salesperson ID'))
            extra.append(lambda line : line.partner_id.user_id.ref)    
            
        if self.show_analytic_account_name:
            header.append(_('Analytic Account'))
            extra.append(lambda line : get_display(line.invoice_id.mapped('invoice_line_ids.account_analytic_id.name')))
            
        if self.show_analytic_account_reference:
            header.append(_('Analytic Account Reference'))
            extra.append(lambda line : get_display(line.invoice_id.mapped('invoice_line_ids.account_analytic_id.code')))
                    
        if self.show_analytic_tags:
            header.append(_('Analytic Tags'))
            extra.append(lambda line : get_display(line.invoice_id.mapped('invoice_line_ids.analytic_tag_ids.name')))                                
        
        header.extend(data['columns'])
        decimal_places = self.currency_id.decimal_places
        rows = [header]        
        title_rows=[]
        group_rows=[]        
        summary_rows = []
        row_merge_cells = []
        empty_rows= []
        
        def format_date(value):
            return self.env['ir.qweb.field.date'].value_to_html(value, {})
        
        for account_data in data['accounts']:            
            title_rows.append(len(rows))
            row_merge_cells.append((len(rows), 0, 2 + len(self.line_ids) + len(extra)))
            totals = [0] * len(self.line_ids)
            for idx in range(len(totals)):
                totals[idx] = account_data['totals'][idx]
                
            rows.append([account_data['account_id'].display_name, None, None, None] + [None] * (len(self.line_ids) + len(extra)))         
            for partner_data in account_data['partners']:
                #row_merge_cells.append((len(rows), 0, 2))
                row =[partner_data['partner_id'].display_name or '', partner_data['partner_id'].ref or '', None, None] + [None] * len(extra)
                row.extend(partner_data['total'])
                if self.show_details:
                    group_rows.append(len(rows))
                rows.append(row)
                if self.show_details:
                    for line in partner_data['details']:
                        move_line = line['move_line']
                        row=[None, None, move_line.move_id.name, format_date(move_line.date_maturity)]
                        for func in extra:
                            value = func(move_line)
                            row.append(value or None)
                            
                        for col in range(len(self.line_ids)):
                            row.append(line[col])
                        rows.append(row)
                    empty_rows.append(len(rows))
                    rows.append([None] * (len(self.line_ids) + 4 + len(extra)))
            
            summary_rows.append(len(rows))
            row_merge_cells.append((len(rows), 0, 2))
            rows.append(['Total', None, None, None] + [None] * len(extra) + totals)   
                                
        title = 'Aged Partner Balance %s' % self.date
        
        char_width = html and 0.5 or 1
        
        formats = {
            'empty_format' : {
                'top' : 1,
                'bottom' : 1,
                }
            }
        
        data = dict(
            rows = rows,
            action = 'record',
            title_rows=title_rows, 
            group_rows=group_rows, 
            decimal_places = decimal_places, 
            add_row_total= None, 
            header_rows_count = 1,
            pdf = pdf,
            html = html,
            filename = title,
            worksheet_name = title,
            summary_rows = summary_rows,
            char_width = char_width,
            row_merge_cells = row_merge_cells,
            empty_rows = empty_rows,
            formats= formats)
        
        if pdf or html:
            data.update({
                'report_title' : title,
                'filename' : title,
                'layout' : 'external',
                })
            rows = self.env['oi_excel_export']._eval_rows(rows)                    
            action = self.env['oi_excel_export'].export_qweb(data)
            if html:
                action['report_type'] = 'qweb-html'
            return action

                    
        excel_id= self.env['oi_excel_export'].export(**data) 
        
        excel_record = self.env['oi_excel_export'].browse(excel_id)
        if (pdf or html) and self._context.get('preview'):
            return excel_record.action_preview_pdf('Preview')
        
        return excel_record.action_download()                         
                    
    def clear_form(self):
        default = self.default_get(list(self._fields))
        for name, field in self._fields.items():
            if field.automatic:
                continue
            elif name in default:
                self[name]= default.get(name)            
            elif field.type in ['one2many', 'many2many']:
                self.write({name : [(5,)]})
            elif not field.required:
                self[name] = False
        self._onchage_template_id()
        return {
            'type' : 'ir.actions.client',
            'tag' : 'trigger_reload',
            }
                    