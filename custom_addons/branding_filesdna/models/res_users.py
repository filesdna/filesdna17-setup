from odoo import models, fields, api


class ResUsers(models.Model):
    
    _inherit = 'res.users'
    
    #----------------------------------------------------------
    # Properties
    #----------------------------------------------------------
    
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'dialog_size',
            'sidebar_type',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'dialog_size',
            'sidebar_type',
        ]


    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    dialog_size = fields.Selection(
        selection=[
            ('minimize', 'Minimize'),
            ('maximize', 'Maximize'),], string="Dialog Size", default='minimize', required=True, )

    sidebar_type = fields.Selection(
        selection=[
            ('invisible', 'Invisible'),
            ('small', 'Small'),
            ('large', 'Large')], string="Sidebar Type", default='large', required=True, )

    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in Filesdna')],
        'Notification', required=True, default='email',
        compute='_compute_notification_type', inverse='_inverse_notification_type', store=True,
        help="Policy on how to handle Chatter notifications:\n"
             "- Handle by Emails: notifications are sent to your email address\n"
             "- Handle in Filesdna: notifications appear in your Filesdna Inbox")