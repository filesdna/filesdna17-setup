from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    human_backend = fields.Selection([
        ('webgl', 'webgl'),
        ('humangl', 'humangl'),
        ('wasm', 'wasm')], string='Backend', default='webgl', required=True, config_parameter='faceid_authentication.human_backend')
    human_similarity = fields.Char(string='Face Similarity', default=55, size=2, config_parameter='faceid_authentication.human_similarity')
    human_blinkdetection = fields.Boolean(string='Validate Blink Detection', default=True, config_parameter='faceid_authentication.human_blinkdetection')
    human_facingcenter = fields.Boolean(string='Validate Facing Center', default=True, config_parameter='faceid_authentication.human_facingcenter')
    human_lookingcenter = fields.Boolean(string='Validate Looking Center', default=True, config_parameter='faceid_authentication.human_lookingcenter')
    human_antispoofcheck = fields.Boolean(string='Validate Anti SpoofCheck', default=True, config_parameter='faceid_authentication.human_antispoofcheck')
    human_livenesscheck = fields.Boolean(string='Validate Liveness Check', default=True, config_parameter='faceid_authentication.human_livenesscheck')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            human_backend = self.env['ir.config_parameter'].get_param('faceid_authentication.human_backend') or 'webgl',
            human_similarity = self.env['ir.config_parameter'].get_param('faceid_authentication.human_similarity') or 55,
            human_blinkdetection = self.env['ir.config_parameter'].get_param('faceid_authentication.human_blinkdetection') or False,
            human_facingcenter = self.env['ir.config_parameter'].get_param('faceid_authentication.human_facingcenter') or False,
            human_lookingcenter = self.env['ir.config_parameter'].get_param('faceid_authentication.human_lookingcenter') or False,
            human_antispoofcheck = self.env['ir.config_parameter'].get_param('faceid_authentication.human_antispoofcheck') or False,
            human_livenesscheck = self.env['ir.config_parameter'].get_param('faceid_authentication.human_livenesscheck') or False,
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_backend', self.human_backend)
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_similarity', self.human_similarity)
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_blinkdetection', self.human_blinkdetection)
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_facingcenter', self.human_facingcenter)
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_lookingcenter', self.human_lookingcenter)
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_antispoofcheck', self.human_antispoofcheck)
        self.env['ir.config_parameter'].sudo().set_param('faceid_authentication.human_livenesscheck', self.human_livenesscheck)
        return res

    @api.constrains('human_similarity')
    def _check_human_similarity(self):
        for company in self:
            if len(company.human_similarity) == 2:
                try: 
                    if isinstance(int(self.human_similarity), int):
                        pass
                    else:
                        raise ValidationError(_("Only Integer(Number) Should Be Used As A Similarity!"))
                except:
                    raise ValidationError(_("Only Integer(Number) Should Be Used As A Similarity!"))
            else:
                raise ValidationError(_("The Length of a Similarity Should Be two!"))
    
