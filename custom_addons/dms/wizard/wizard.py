from odoo import models, fields, api
from odoo.exceptions import UserError

class iTrackLinkWizard(models.TransientModel):
    _name = 'dms.itrack.link.wizard'
    _description = 'DMS iTrack Link'

    ref_id = fields.Many2one(comodel_name='itrack.type.eat', string='Referance Number')
    user_ids = fields.Many2many(comodel_name='res.users', string='Assignes')
    due_date = fields.Date(string='Date Line')
    message = fields.Html('Message')

    def action_submit(self):
        for record in self:
            user = record.env.user
            active_id = record._context['active_id']
            file_record = self.env['dms.file'].search([('id','=',active_id)])
            in_out_id = file_record.in_out
            itrack_doc_type = self.env['itrack.document.type']
            doc_type_id = itrack_doc_type.search([('name','ilike',file_record.confidentiality_level_id.name)])
            itrack_priorty = self.env['itrack.priority.eat']
            itrack_priorty_id = itrack_priorty.search([('name','ilike',file_record.priority_id.name)])

            if not doc_type_id:
                doc_type_id = itrack_doc_type.create({
                    'name':file_record.confidentiality_level_id.name
                })

            if not itrack_priorty_id:
                itrack_priorty_id = itrack_priorty.create({
                    'name':file_record.priority_id.name
                })
            print(in_out_id)
            itrack_id = self.env['itrack.document.eat'].create({
                'image_1920':file_record.image_1920,
                'requester_id':user.id,
                'department_id':user.employee_id.department_id.id,
                'itrack_type_id':self.ref_id.id,
                'in_out_id':in_out_id,
                'int_exp_id':doc_type_id.id,
                'priority_id':itrack_priorty_id.id,
                'stage_id':1
            })
            print("::::::::::::::::::::::::",itrack_id)
            itrack_id.dms_line_ids = file_record.ids
            for assign_id in self.user_ids:
                requests = []
                requests.append({
                    'track_id': itrack_id.id,
                    'requester_id': self.env.uid,
                    'assign_to_id': assign_id.id,
                    'request_date': fields.Datetime.now(),
                    'request_message': self.message,
                })
                itrack_requests = self.env['itrack.request.eat'].create(requests)
                itrack_requests.notify_user()
                # create_dms_line = self.env['dms.line'].create({
                #     'file_id': file_record.id,
                #     'requester_id': itrack_requests.requester_id.name,
                #     'request_date': self.due_date,
                #     'assign_to_id': itrack_requests.assign_to_id.name,
                #     'response_date': itrack_requests.response_date,
                #     'state': itrack_requests.state,
                #     'request_message': itrack_requests.request_message,
                #
                # })
                # print('create_dms_line=', create_dms_line)

            return {
                'effect': {
                    'fadeout': 'fast',
                    'message': 'iTrack created successfully.',
                    'type': 'rainbow_man',
                }
            }

