# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PartnerSocialMedia(models.Model):
    _inherit = 'res.partner'


    line_social_ids = fields.One2many(comodel_name='res.partner.socail.line', inverse_name='partner_id', string='Social Media')
    



class PartnerSocialMedia(models.Model):
    _name = 'res.partner.socail.line'

    partner_id = fields.Many2one(comodel_name='res.partner', string='Contact')
    link  = fields.Char(string="URL", 
    required=True
    )
    
    social_platform = fields.Selection([
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter (now X)'),
        ('linkedin', 'LinkedIn'),
        ('snapchat', 'Snapchat'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube'),
        ('pinterest', 'Pinterest'),
        ('reddit', 'Reddit'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('wechat', 'WeChat'),
        ('discord', 'Discord'),
        ('tumblr', 'Tumblr'),
        ('vimeo', 'Vimeo'),
        ('flickr', 'Flickr'),
        ('quora', 'Quora'),
        ('clubhouse', 'Clubhouse'),
        ('signal', 'Signal'),
        ('medium', 'Medium'),
        ('twitch', 'Twitch'),
        ('soundcloud', 'SoundCloud'),
        ('github', 'GitHub'),
        ('dribbble', 'Dribbble'),
        ('behance', 'Behance')
    ], string='Social Platform',required=True,default='facebook')
    comment  = fields.Char(string="Comment")



