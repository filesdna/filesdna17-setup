from odoo import models, fields, api

class DocumentSign(models.Model):
    _name = 'document.sign'
    _description = 'Document Sign'

    document_id = fields.Many2one('dms.file', string="Document", ondelete='cascade')
    company_id = fields.Char(string="Company ID")
    email = fields.Char(string="Email", required=True)
    user_hash = fields.Char(string="User Hash", required=True)
    order_by = fields.Integer(string="Order By", required=True)
    status = fields.Selection([
        ('Draft', 'Draft'),
        ('Pending', 'Pending'),
        ('Signed', 'Signed'),
        ('Declined', 'Declined')
    ], string="Status", required=True, default='Draft')
    is_guest = fields.Integer(string="Is Guest", required=True)
    reason = fields.Char(string="Reason")
    sent_by = fields.Char(string="Sent By", required=True)
    sent_by_email = fields.Char(string="Sent By Email", required=True)
    date = fields.Datetime(string="Date")
    delegate_email = fields.Char(string="Delegate Email")
    security_type = fields.Selection([
        ('two_factor', 'Two Factor'),
        ('finger_print', 'Fingerprint'),
        ('nfc', 'NFC'),
        ('six_digit', 'Six Digit'),
        ('classified', 'Classified'),
        ('two_factor_microsoft', 'Two Factor Microsoft'),
        ('is_verify_voice', 'Voice Verification'),
        ('is_verify_liveness', 'Liveness Verification'),
        ('is_verify_uaepass', 'UAE Pass Verification'),
        ('sms_security', 'SMS Security'),
        ('', 'None')
    ], string="Security Type")
    platform = fields.Selection([
        ('mobile', 'mobile'),
        ('website', 'website')
    ], string="Platform")
    voice_code = fields.Char(string="Voice Code")
    is_last_completed = fields.Boolean(string="Is Last Completed", default=False)
    ccuser_email = fields.Char(string="CC User Email")
    number_fill_by = fields.Char(string="Number Fill By")
    sms_country = fields.Char(string="SMS Country")
    sms_phone_no = fields.Char(string="SMS Phone Number")
