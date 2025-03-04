import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError
from odoo.addons.smartform.services.helpers import serialize_record

_logger = logging.getLogger(__name__)

class InviteCreateController(http.Controller):

    @http.route('/invite/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_invite(self, **kwargs):
        try:
            # Extract input parameters
            form = kwargs.get('form')
            from_user = kwargs.get('from')
            to_user = kwargs.get('to')
            message = kwargs.get('message')
            link = kwargs.get('link')
            done = kwargs.get('done', '0')  # Default to 0 (Pending)

            if not (form and from_user and to_user and message and link):
                raise UserError("All required fields must be provided.")


            # Check for duplicate invite
            invite_count = request.env['invite'].sudo().search_count([
                ('form', '=', form),
                ('from_user', '=', from_user),
                ('to_user', '=', to_user),
                ('done', '=', '0')
            ])

            if invite_count:
                response_data = {'message': "Already sent an invitation to this email.", 'success': False}
                return Response(json.dumps(response_data), status=400, mimetype='application/json')

            # Prepare the HTML content
            html = f"""
                <div style='text-align: center; padding: 50px 20px;'>
                    <h2>Hello {to_user}</h2>
                    <hr/>
                    <p>{message}<br/>
                    Please fill the form by clicking this <a href='https://{link}'>link</a> or the button below:</p>
                    <br/>
                    <a style='padding: 5px 20px; color: white; background: green;' href='https://{link}'>Fill Form</a>
                </div>
            """

            # Create the email data
            mail_data = {
                'subject': f"You received an invitation to fill a form from {from_user}",
                'body_html': html,
                'email_to': to_user,
                'email_from': 'no-reply@filesdna.com',
            }

            # Create and send the email
            mail = request.env['mail.mail'].sudo().create(mail_data)
            mail.send()

            # Create the invite record
            invite_data = {
                'form': form,
                'from_user': from_user,
                'to_user': to_user,
                'message': message,
                'done': done,
            }
            invite = request.env['invite'].sudo().create(invite_data)
            
            serialized_data = serialize_record(invite.read()[0])

            response_data = {
                'message': "Invite sent!",
                'data': serialized_data,
                'success': True,
            }
            return Response(json.dumps(response_data), status=200, mimetype='application/json')

        except UserError as e:
            _logger.error(f"UserError: {str(e)}")
            response_data = {'message': str(e), 'success': False}
            return Response(json.dumps(response_data), status=400, mimetype='application/json')

        except Exception as e:
            _logger.error(f"Error sending invite: {str(e)}")
            response_data = {'message': "Error sending invite.", 'success': False}
            return Response(json.dumps(response_data), status=500, mimetype='application/json')
