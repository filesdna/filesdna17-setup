import os
from odoo import models, api
from odoo.http import request
from odoo.addons.dms_editor.services.google_storage import LocalStorageService
from odoo.tools import config
import logging

_logger = logging.getLogger(__name__)

 
server_path = config['server_path']

class CommentService:
    def __init__(self):
        self.gcs_service = LocalStorageService()

    def set_picture(self, picture):
        """Set the picture URL."""
        if "storage.cloud.google.com" in picture:
            return self.gcs_service.read_url(picture)
        return picture

    def set_voice(self, voice):
        """Set the voice URL."""
        return self.gcs_service.read_url(voice)

    def set_comment(self, data, user_id):
        """Process comments with privacy and additional fields."""
        result = []
        for item in data:
            user = item.get("user_id", {})
            if item.get("privacy") == "private" and user.get("id") != user_id:
                continue
            item["picture"] = self.set_picture(user.get("picture", ""))
            if item.get("comment_type") == "voice":
                item["message"] = self.set_voice(item.get("message"))
            item["first_name"] = user.get("first_name")
            item["last_name"] = user.get("last_name")
            item["email"] = user.get("email")
            item.pop("user_id", None)
            item["replies"] = self.set_reply(item.get("id"))
            result.append(item)
        return result

    def set_reply(self, comment_id):
        """Process replies to a comment."""
        Reply = request.env["document.reply"].sudo()
        replies = Reply.search_read(
            [("comment_id", "=", comment_id)],
            ["createdat", "user_id", "message", "reply_type"],
            order="id ASC"
        )
        result = []
        for reply in replies:
            user = reply.get("user_id", {})
            reply["picture"] = self.set_picture(user.get("picture", ""))
            if reply.get("reply_type") == "voice":
                reply["message"] = self.set_voice(reply.get("message"))
            reply["first_name"] = user.get("first_name")
            reply["last_name"] = user.get("last_name")
            reply["email"] = user.get("email")
            reply.pop("user_id", None)
            result.append(reply)
        return result

    def get_comments(self, page_id, user_id):
        """Retrieve comments for a page."""
        comments = request.env["document.comments"].sudo().search_read(
            [("page_id", "=", page_id)],
            ["createdat", "position", "message", "comment_type", "privacy", "duration", "user_id"]
        )
        return self.set_comment(comments, user_id)
