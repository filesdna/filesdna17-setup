from odoo.http import request
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

def mail_data(email_type, subject, email_to, header, description,hash_key=None,attachment_data=None,attachment_name=None, base_url=None, content=None):
    link = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    if email_type == "workflow_invitation":
        html_body = f"""
        <div style="width: 100%; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); text-align: center; border: 1px solid #ddd;">
                <div style="background-color: #ffffff; padding: 20px;">
                    <img src="{link}/dms_editor/static/src/images/logo2.png" alt="FilesDNA Logo" style="width: 250px;">
                </div>
                <div style="padding: 30px; background-color: #f7fdfd;">
                    <p style="font-size: 18px; font-weight: bold; margin: 0; color: #333;">{header}</p>
                    <p style="font-size: 16px; margin: 15px 0; color: #555;">{description}</p>
                </div>
                <div style="padding: 20px; background-color: #f9f9f9; font-size: 14px; color: #666;">
                    <p>Online PDF Editor and e-Signature Solution</p>
                    <div style="margin: 10px 0;">
                        <a href="https://apps.apple.com/in/app/filesdna/id1546580912"><img src="{link}/dms_editor/static/src/images/apple-store.png" alt="App Store" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                        <a href="https://play.google.com/store/apps/details?id=com.filesdna"><img src="{link}/dms_editor/static/src/images/google-play.png" alt="Google Play" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="https://www.filesdna.com/privacy-policy" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Privacy Policy</a> | 
                        <a href="https://www.filesdna.com/contact-us" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Contact Us</a>
                    </div>
                    <p style="margin-top: 10px; font-size: 12px; color: #aaa;">{datetime.now().year} © Files DNA - Documents Management System | All Rights Reserved</p>
                </div>
        </div>
        """
        mail_data = {
            'subject': subject,
            'body_html': html_body,
            'email_to': email_to,
            'email_from': 'no-reply@filesdna.com',
        }

    elif email_type == "workflow_assign":
        html_body = f"""
        <div style="width: 100%; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); text-align: center; border: 1px solid #ddd;">
                <div style="background-color: #ffffff; padding: 20px;">
                    <img src="{link}/dms_editor/static/src/images/logo2.png" alt="FilesDNA Logo" style="width: 250px;">
                </div>
                <div style="padding: 30px; background-color: #f7fdfd;">
                    <p style="font-size: 18px; font-weight: bold; margin: 0; color: #333;">{header}</p>
                    <p style="font-size: 16px; margin: 15px 0; color: #555;">{description}</p>
                    <p style="font-size: 14px; margin: 10px 0; color: #888;">If you are having any issues with your account, please don’t hesitate to contact us by sending email to support@filesdna.com</p>
                    <br/>Please review submitted data by clicking this <a href='{base_url}'>link</a> or below button</p>
                    <br/>
                    <a href="{base_url}" style="display: inline-block; padding: 12px 20px; margin: 20px 0; background-color: #00b5ad; color: #fff; text-decoration: none; font-weight: bold; border-radius: 4px; box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2); transition: all 0.2s ease;">Fill Form</a>
                </div>
                <div style="padding: 20px; background-color: #f9f9f9; font-size: 14px; color: #666;">
                    <p>Online PDF Editor and e-Signature Solution</p>
                    <div style="margin: 10px 0;">
                        <a href="https://apps.apple.com/in/app/filesdna/id1546580912"><img src="{link}/dms_editor/static/src/images/apple-store.png" alt="App Store" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                        <a href="https://play.google.com/store/apps/details?id=com.filesdna"><img src="{link}/dms_editor/static/src/images/google-play.png" alt="Google Play" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="https://www.filesdna.com/privacy-policy" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Privacy Policy</a> | 
                        <a href="https://www.filesdna.com/contact-us" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Contact Us</a>
                    </div>
                    <p style="margin-top: 10px; font-size: 12px; color: #aaa;">{datetime.now().year} © Files DNA - Documents Management System | All Rights Reserved</p>
                </div>
        </div>
        """
        mail_data = {
            'subject': subject,
            'body_html': html_body,
            'email_to': email_to,
            'email_from': 'no-reply@filesdna.com',
        }
    elif email_type == "workflow_report_approval":
        html_body = f"""
        <div style="width: 100%; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); text-align: center; border: 1px solid #ddd;">
                <div style="background-color: #ffffff; padding: 20px;">
                    <img src="{link}/dms_editor/static/src/images/logo2.png" alt="FilesDNA Logo" style="width: 250px;">
                </div>
                <div style="padding: 30px; background-color: #f7fdfd;">
                    <p style="font-size: 18px; font-weight: bold; margin: 0; color: #333;">{header}</p>
                    <p style="font-size: 16px; margin: 15px 0; color: #555;">{description}</p>
                    <p style="font-size: 14px; margin: 10px 0; color: #888;">If you are having any issues with your account, please don’t hesitate to contact us by sending email to support@filesdna.com</p>
                    <br/>
                    {content}
                </div>
                <div style="padding: 20px; background-color: #f9f9f9; font-size: 14px; color: #666;">
                    <p>Online PDF Editor and e-Signature Solution</p>
                    <div style="margin: 10px 0;">
                        <a href="https://apps.apple.com/in/app/filesdna/id1546580912"><img src="{link}/dms_editor/static/src/images/apple-store.png" alt="App Store" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                        <a href="https://play.google.com/store/apps/details?id=com.filesdna"><img src="{link}/dms_editor/static/src/images/google-play.png" alt="Google Play" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="https://www.filesdna.com/privacy-policy" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Privacy Policy</a> | 
                        <a href="https://www.filesdna.com/contact-us" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Contact Us</a>
                    </div>
                    <p style="margin-top: 10px; font-size: 12px; color: #aaa;">{datetime.now().year} © Files DNA - Documents Management System | All Rights Reserved</p>
                </div>
        </div>
        """
        mail_data = {
            'subject': subject,
            'body_html': html_body,
            'email_to': email_to,
            'email_from': 'no-reply@filesdna.com',
        }

    elif email_type == "workflow_email":
        html_body = f"""
        <div style="width: 100%; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); text-align: center; border: 1px solid #ddd;">
                <div style="background-color: #ffffff; padding: 20px;">
                    <img src="{link}/dms_editor/static/src/images/logo2.png" alt="FilesDNA Logo" style="width: 250px;">
                </div>
                <div style="padding: 30px; background-color: #f7fdfd;">
                    <p style="font-size: 18px; font-weight: bold; margin: 0; color: #333;">{header}</p>
                    <p style="font-size: 16px; margin: 15px 0; color: #555;">{description}</p>
                    <p style="font-size: 16px; margin: 15px 0; color: #555;">{content}</p>
                    <br/>
                    <p style="font-size: 14px; margin: 10px 0; color: #888;">If you are having any issues with your account, please don’t hesitate to contact us by sending email to support@filesdna.com</p>
                </div>
                <div style="padding: 20px; background-color: #f9f9f9; font-size: 14px; color: #666;">
                    <p>Online PDF Editor and e-Signature Solution</p>
                    <div style="margin: 10px 0;">
                        <a href="https://apps.apple.com/in/app/filesdna/id1546580912"><img src="{link}/dms_editor/static/src/images/apple-store.png" alt="App Store" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                        <a href="https://play.google.com/store/apps/details?id=com.filesdna"><img src="{link}/dms_editor/static/src/images/google-play.png" alt="Google Play" style="width: 120px; margin: 0 10px; display: inline-block;"></a>
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="https://www.filesdna.com/privacy-policy" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Privacy Policy</a> | 
                        <a href="https://www.filesdna.com/contact-us" style="text-decoration: none; color: #00b5ad; margin: 0 5px;">Contact Us</a>
                    </div>
                    <p style="margin-top: 10px; font-size: 12px; color: #aaa;">{datetime.now().year} © Files DNA - Documents Management System | All Rights Reserved</p>
                </div>
        </div>
        """
        mail_data = {
            'subject': subject,
            'body_html': html_body,
            'email_to': email_to,
            'email_from': 'no-reply@filesdna.com',
        }

    # Create and send the email
    mail = request.env['mail.mail'].sudo().create(mail_data)
    _logger.info(f"mail:{mail}")
    mail.send()