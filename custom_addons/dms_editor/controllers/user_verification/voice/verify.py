import os
import logging
import json
import base64
from datetime import datetime
from odoo import http
from odoo.http import request, Response
import requests
from werkzeug.utils import secure_filename
from odoo.tools import config
import librosa
import soundfile as sf

_logger = logging.getLogger(__name__)

server_path = config['server_path']

class VoiceVerificationController(http.Controller):

    @http.route(['/api/voice-non-user/<string:callType>','/api/voice/<string:callType>','/api/file/<string:callType>'], type='http', auth='public', methods=['POST'], csrf=False)
    def verify_voice(self, callType, **kwargs):
        try:
            # Parse input parameters
            token = kwargs.get('token', 'gloryvoicefootprint')  # Default token
            platform = kwargs.get('platform', 'web')  # Default platform
            call_type = callType if callType else 'verify'  # Call type
            free_user = kwargs.get('freeUser', False)

            # Get user details
            user = request.env.user
            user_email = user.email
            email = user_email if (kwargs.get('email') == 'null' or not kwargs.get('email')) else kwargs.get('email')
            user_id = user.id
            user_verification = request.env['user.verification'].sudo().search([('user_id', '=', user.id)])
            # Check for uploaded audio file
            audio_file = request.httprequest.files.get('audio')
            if not audio_file:
                return self._response_error("Audio file is required.")

            # Save the uploaded file
            temp_path = f'{server_path}/dms_editor/static/src/temp'
            os.makedirs(temp_path, exist_ok=True)
            file_name = secure_filename(audio_file.filename)
            local_file_path = os.path.join(temp_path, file_name)

            with open(local_file_path, 'wb') as f:
                f.write(audio_file.read())

            # Convert audio for 'app' platform if required
            if platform == "app":
                # Generate the output WAV file path
                converted_file = os.path.join(temp_path, f"{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
                
                # Load the audio file using librosa
                audio, sr = librosa.load(local_file_path, sr=None)  # Preserve original sample rate
                
                # Save the audio as a WAV file
                sf.write(converted_file, audio, sr)
                
                # Remove the original file
                os.remove(local_file_path)
                
                # Return the converted file path
                local_file_path = converted_file

            # Prepare API request to external service
            url = "https://voice-reco-europe.filesdna.com/verify"
            headers = {'accept': 'application/json'}
            files = {'audio': open(local_file_path, 'rb')}
            _logger.info(f"email:{email}")
            data = {'token': token, 'name': email}

            response = requests.post(url, headers=headers, files=files, data=data)
            response_data = response.json()

            # Clean up the local file
            self._delete_file(local_file_path)

            # Handle API response
            _logger.info(f"response_data:{response_data}")

            _logger.info(f"response_data.get('status'):{response_data.get('status')}")
            if response.status_code == 200 and response_data.get('status') == 'success':
                confidence = float(response_data.get('confidence', 0))
                result = response_data.get('result', 'False').lower() == 'true'

                # Verify confidence and update user verification status
                if result and confidence > 0.8:
                    request.env['user.verification'].sudo().search([('user_id', '=', user.id)]).write({ 'is_verify_voice': 1 })
                    return self._response_success({
                        "success": True,
                        "status": response_data.get('status'),
                        "message": response_data.get('message'),
                        "confidence": response_data.get('confidence'),
                        "result": result
                    })
                return self._response_error("Voice verification failed.")
            else:
                return self._response_error("Failed to verify voice.")

        except Exception as e:
            _logger.error(f"Error in voice verification: {str(e)}")
            return self._response_error("An error occurred during voice verification.")

    # Helper to delete temporary files
    def _delete_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            _logger.error(f"Failed to delete file {file_path}: {str(e)}")

    # Helper for error response
    def _response_error(self, message, status=400):
        return Response(
            json.dumps({"success": False, "message": message}),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    # Helper for success response
    def _response_success(self, data):
        return Response(
            json.dumps(data),
            headers={'Content-Type': 'application/json'},
            status=200
        )
