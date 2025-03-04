from odoo import api, fields, models, modules, _
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
import uuid

class ResUsers(models.Model):    
    _inherit = 'res.users'
    
    @api.model
    def get_faceid_token(self):
        if not self.faceid_token:
            self.sudo().write({
                'faceid_token': str(uuid.uuid4())
            })
        return self.faceid_token
    
    faceid_token = fields.Char("Integration Token", default=get_faceid_token, store=False)
    user_faces = fields.One2many("res.users.faces", "user_id", "Faces")
    
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['user_faces']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['user_faces']
    
class ResUsersFaces(models.Model):
    _name = "res.users.faces"
    _description = "Face Recognition Images"
    _inherit = ['image.mixin']
    _order = 'id'

    user_id = fields.Many2one("res.users", "User", index=True, ondelete='cascade')
    login = fields.Char(related="user_id.login", string="User Login", readonly=True, store=True)
    name = fields.Char("Name", related='user_id.name')
    image = fields.Binary("Images")
    descriptor = fields.Text(string='Face Descriptor')
    has_descriptor = fields.Boolean(string="Has Face Descriptor",default=False, compute='_compute_has_descriptor', readonly=True, store=True)
    
    @api.depends('descriptor')
    def _compute_has_descriptor(self):
        for rec in self:
            rec.has_descriptor = True if rec.descriptor else False

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'user_id',
            'login',
            'name',
            'image',
            'descriptor',
            'has_descriptor',
        ]
        
    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'user_id',
            'login',
            'name',
            'image',
            'descriptor',
            'has_descriptor',
        ]
