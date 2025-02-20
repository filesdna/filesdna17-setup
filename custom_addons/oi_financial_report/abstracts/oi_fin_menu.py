'''
Created on May 24, 2017

@author: Zuhair Hammadi
'''
from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)

class Menu(models.AbstractModel):
    _name ='oi_fin.menu'
    _description = 'oi_fin.menu'
    _template_col = ''
    _transient_model=''
    
    menu_id = fields.Many2one('ir.ui.menu', copy = False)
    action_id = fields.Many2one('ir.actions.act_window', copy = False)
    
    
    def create_menu(self):
        self = self.exists()
        _logger.info('create_menu %s' % [self, self.display_name])
        for record in self:
            val = {
                'name': record.name,
                'res_model': self._transient_model,
                'view_mode': 'form',
                'target' : 'inline',
                'context' : {'default_%s' % self._template_col : record.id,
                             'hide_rows_columns' : True
                             }
            }
            if self.action_id:
                self.action_id.write(val)
                action_id = self.action_id
            else:
                action_id = self.env['ir.actions.act_window'].create(val)
            menu_root = self.env.ref('oi_financial_report.menu_root') 
            if record.menu_id:
                menu_id = record.menu_id
            else:                                   
                menu_id=self.env['ir.ui.menu'].create({
                    'name': record.name,
                    'parent_id': menu_root.id,
                    'action': 'ir.actions.act_window,%d' % (action_id.id,),
                })
            record.write({'menu_id' : menu_id.id, 'action_id' : action_id.id})
        return {'type':'ir.actions.act_window_close'}        
        
    
    def drop_menu(self):        
        self.mapped('menu_id').unlink()
        self.mapped('action_id').unlink()
    
    
    def unlink(self):
        self.drop_menu()
        return super(Menu, self).unlink()
    