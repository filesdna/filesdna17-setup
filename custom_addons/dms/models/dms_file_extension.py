from odoo import models, fields


class DMSFileExtension(models.Model):
    _name = 'dms.file.extension'
    _description = 'DMS File Extensions'

    file_extension_selection = [
        ('txt', 'Text File (.txt)'),
        ('pdf', 'PDF File (.pdf)'),
        ('zip', 'Zip File (.zip)'),
        ('doc', 'Word Document (.doc)'),
        ('docx', 'Word Document (.docx)'),
        ('xls', 'Excel Spreadsheet (.xls)'),
        ('csv', 'Excel Spreadsheet (.csv)'),
        ('xlsx', 'Excel Spreadsheet (.xlsx)'),
        ('pptx', 'Power Point (.pptx)'),
        ('png', 'Image (.png)'),
        ('jpeg', 'Image (.jpeg)'),
        ('jpg', 'Image (.jpg)'),
        ('no_name', 'No_Name'),
    ]

    name = fields.Selection(
        file_extension_selection,
        string='File Extension',
    )
    file_image = fields.Image("File Image", max_width=64, max_height=64)
