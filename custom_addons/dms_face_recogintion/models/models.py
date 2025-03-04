import base64
import face_recognition
import numpy as np
from odoo import models, api
from io import BytesIO
from PIL import Image

class YourModel(models.Model):
    _inherit = 'dms.file'



    def unlock(self):
        if self.directory_id:
            groups = self.directory_id.complete_group_ids.ids
            self.has_permission(groups_ids=groups, permission='perm_lock')
            self.decrypt_content()
            self.write({"locked_by": None, 'is_locked': False})
            # if self.extension == 'png':
            return {
                    'type': 'ir.actions.client',
                    'tag': 'face_recognition_component',
                }


    @api.model
    def recognize_face(self, image_data):
        image_data = image_data.split(",")[1]
        image = Image.open(BytesIO(base64.b64decode(image_data)))
        image = np.array(image)

        # Load known faces from user profiles
        known_face_encodings = []
        known_face_names = []

        users = self.env['res.users'].search([])
        for user in users:
            if user.image_1920:
                face_image = Image.open(BytesIO(base64.b64decode(user.image_1920)))
                face_image = np.array(face_image)
                face_encoding = face_recognition.face_encodings(face_image)
                if face_encoding:
                    known_face_encodings.append(face_encoding[0])
                    known_face_names.append(user.id)

        # Recognize faces in the captured image
        face_encodings = face_recognition.face_encodings(image)
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            if True in matches:
                first_match_index = matches.index(True)
                user_id = known_face_names[first_match_index]
                return user_id
        return False
