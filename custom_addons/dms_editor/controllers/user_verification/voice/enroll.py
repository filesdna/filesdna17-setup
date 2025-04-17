from odoo import http
from odoo.http import request, Response
import json
import os
import logging
import requests
import shutil
import subprocess
from werkzeug.utils import secure_filename
from odoo.tools import config
import librosa
import soundfile as sf

_logger = logging.getLogger(__name__)

# Configuration Variables
server_path = config['server_path']

TEMP_DIR = f'{server_path}/dms_editor/static/src/temp'

class VoiceEnrollmentController(http.Controller):

    @http.route(['/api/voice/enroll','/api/voice-non-user/enroll'], type='http', auth='public', methods=['POST'], csrf=False)
    def enroll_master_voice(self, **kwargs):
        try:
            # Get user and input details
            user = request.env.user
            email = kwargs.get('email', user.email)
            token = kwargs.get('token', 'gloryvoicefootprint')
            platform = kwargs.get('platform', 'web')
            
            # Validate uploaded files
            uploaded_files = request.httprequest.files.getlist('audios[]')
            if not uploaded_files or len(uploaded_files) < 5:
                return self._response_error("User must record at least 5 messages to verify voice.")

            # Process uploaded files
            processed_files = []
            try:
                for index, uploaded_file in enumerate(uploaded_files):
                    file_ext = os.path.splitext(uploaded_file.filename)[-1]
                    file_name = f"{self._generate_random_string(10)}-{index + 1}{file_ext}"
                    temp_path = os.path.join(TEMP_DIR, secure_filename(file_name))
                    
                    # Read binary content from uploaded_file
                    with open(temp_path, 'wb') as temp_file:
                        temp_file.write(uploaded_file.read())  # Read and write binary data
                                
                    # Convert to .wav format if platform is 'app'
                    if platform == "app":
                        # Generate a random file name for the WAV output
                        wav_path = os.path.join(TEMP_DIR, f"{self._generate_random_string(10)}-{index + 1}.wav")
                        
                        try:
                            # Load the audio file using librosa
                            audio, sr = librosa.load(temp_path, sr=None)  # Preserve the original sample rate
                            
                            # Save the audio as a WAV file
                            sf.write(wav_path, audio, sr)
                            
                            # Remove the temporary file
                            os.remove(temp_path)
                            
                            # Append the converted file to processed_files
                            processed_files.append(wav_path)
                        except Exception as e:
                            _logger.error(f"Error converting to WAV: {str(e)}")
                    else:
                        # No conversion needed, add the original file
                        processed_files.append(temp_path)

            except Exception as e:
                _logger.error(f"Error processing voice files: {str(e)}")
                self._cleanup_files(processed_files)
                return self._response_error("Failed to process voice files.")

            # Send request to external voice enrollment API
            enroll_response = self._enroll_voice_api(email, processed_files, token)
            
            # Cleanup processed files
            self._cleanup_files(processed_files)

            # Handle API response
            if enroll_response.get('success'):
                # Update user verification status
                request.env['user.verification'].sudo().search([('user_id', '=', user.id)]).write({
                    'is_verify_voice': 1
                })
                return self._response_success(enroll_response)
            else:
                return self._response_error(enroll_response.get('message', 'Failed to enroll voice'))

        except Exception as e:
            _logger.error(f"Error in enroll_master_voice: {str(e)}")
            return self._response_error("An error occurred during enrollment.")

    def _enroll_voice_api(self, name, files, token):
        """
        Send request to external voice enrollment API.
        """
        try:
            url = "https://voice1.filesdna.com/enroll"
            headers = {"accept": "application/json"}
            data = {"token": token, "name": name}
            files_data = [('audios', (os.path.basename(file), open(file, 'rb'), 'audio/wav')) for file in files]
            
            response = requests.post(url, headers=headers, data=data, files=files_data)
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get('status') == "success", "message": result.get('message')}
            else:
                return {"success": False, "message": response.text}
        except Exception as e:
            _logger.error(f"Error in voice enrollment API: {str(e)}")
            return {"success": False, "message": str(e)}

    def _cleanup_files(self, files):
        """
        Remove temporary files.
        """
        for file in files:
            try:
                os.remove(file)
            except Exception as e:
                _logger.error(f"Failed to delete file {file}: {str(e)}")

    def _generate_random_string(self, length):
        """
        Generate a random string of given length.
        """
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _response_success(self, data):
        """
        Success response.
        """
        return Response(
            json.dumps({"success": True, "data": data}),
            headers={'Content-Type': 'application/json'},
            status=200
        )

    def _response_error(self, message, status=400):
        """
        Error response.
        """
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )
