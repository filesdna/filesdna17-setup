import os
import logging
from odoo import models, fields, api
from odoo.tools import config

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class TempFileCleanup(models.Model):
    _name = 'temp.file.cleanup'
    _description = 'Temporary File Cleanup Scheduler'

    # Define the directories to clean
    DIRECTORIES_TO_CLEAN = [
        f'{server_path}/dms_editor/static/src/temp',
        f'{server_path}/dms_editor/static/src/assets/pdf',
        f'{server_path}/dms_editor/static/src/assets/pdf/output',
        f'{server_path}/dms_editor/static/src/assets/signpdf',
        f'{server_path}/dms_editor/static/src/images/preview',
    ]

    @api.model
    def clean_temp_files(self):
        """
        Scheduled job to clean temporary files from specified directories.
        """
        try:
            for directory in self.DIRECTORIES_TO_CLEAN:
                if os.path.exists(directory):
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                os.remove(file_path)
                                _logger.info(f"Deleted file: {file_path}")
                            except Exception as e:
                                _logger.error(f"Failed to delete {file_path}: {str(e)}")
                else:
                    _logger.warning(f"Directory does not exist: {directory}")
        except Exception as e:
            _logger.error(f"Error during temporary file cleanup: {str(e)}")
