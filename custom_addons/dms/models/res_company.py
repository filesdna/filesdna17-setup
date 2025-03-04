
import logging
import hashlib
from odoo import api, fields, models
from cryptography.fernet import Fernet

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):

    _inherit = "res.company"

    # ----------------------------------------------------------
    # Database
    # ----------------------------------------------------------

    documents_onboarding_state = fields.Selection(
        selection=[
            ("not_done", "Not done"),
            ("just_done", "Just done"),
            ("done", "Done"),
            ("closed", "Closed"),
        ],
        default="not_done",
    )

    documents_onboarding_storage_state = fields.Selection(
        selection=[
            ("not_done", "Not done"),
            ("just_done", "Just done"),
            ("done", "Done"),
            ("closed", "Closed"),
        ],
        default="not_done",
    )

    documents_onboarding_directory_state = fields.Selection(
        selection=[
            ("not_done", "Not done"),
            ("just_done", "Just done"),
            ("done", "Done"),
            ("closed", "Closed"),
        ],
        default="not_done",
    )

    documents_onboarding_file_state = fields.Selection(
        selection=[
            ("not_done", "Not done"),
            ("just_done", "Just done"),
            ("done", "Done"),
            ("closed", "Closed"),
        ],
        default="not_done",
    )
    encription_key = fields.Char(string='Encryption Key' , compute="compute_encription_key", readonly=True, store=True)
    encryption_icon = fields.Image("Encryption Icon", max_width=128, max_height=128)
    image_lines = fields.One2many(comodel_name='res.company.dms', inverse_name='company_id', string='')
    
    

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------
    @api.depends('name')
    def compute_encription_key(self):
        for rec in self:
            try:
                key = Fernet.generate_key()  
                rec.encription_key = key
            except UnicodeDecodeError:
                rec.encription_key = "Error: Non-UTF-8 encoded login"

    def get_and_update_documents_onboarding_state(self):
        return self.get_and_update_onbarding_state(
            "documents_onboarding_state", self.get_documents_steps_states_names()
        )

    def get_documents_steps_states_names(self):
        return [
            "documents_onboarding_storage_state",
            "documents_onboarding_directory_state",
            "documents_onboarding_file_state",
        ]

    # ----------------------------------------------------------
    # Actions
    # ----------------------------------------------------------

    @api.model
    def action_open_documents_onboarding_storage(self):
        return self.env.ref("dms.action_dms_storage_new").read()[0]

    @api.model
    def action_open_documents_onboarding_directory(self):
        storage = self.env["dms.storage"].search([], order="create_date desc", limit=1)
        action = self.env.ref("dms.action_dms_directory_new").read()[0]
        action["context"] = {
            **self.env.context,
            **{
                "default_is_root_directory": True,
                "default_storage_id": storage and storage.id,
            },
        }
        return action

    @api.model
    def action_open_documents_onboarding_file(self):
        directory = self.env["dms.directory"].search(
            [], order="create_date desc", limit=1
        )
        action = self.env.ref("dms.action_dms_file_new").read()[0]
        action["context"] = {
            **self.env.context,
            **{"default_directory_id": directory and directory.id},
        }
        return action

    @api.model
    def action_close_documents_onboarding(self):
        self.env.user.company_id.documents_onboarding_state = "closed"

class ResCompanyImages(models.Model):

    _name = 'res.company.dms'
    _description = ''


    FILE_EXTENSION_SELECTION = [
        ('txt', 'Text File (.txt)'),
        ('pdf', 'PDF File (.pdf)'),
        ('doc', 'Word Document (.doc)'),
        ('docx', 'Word Document (.docx)'),
        ('xls', 'Excel Spreadsheet (.xls)'),
        ('xlsx', 'Excel Spreadsheet (.xlsx)'),
        ('pptx', 'Power Point (.pptx)'),
    ]


    company_id  = fields.Many2one(comodel_name='res.company', string='')
    file_image = fields.Image("File Image", max_width=128, max_height=128,required=True)
    file_extension = fields.Selection(
        FILE_EXTENSION_SELECTION,
        string='File Extension',
        help='Select the file extension type.',
        required=True
    )
   


   