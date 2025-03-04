# -*- coding: utf-8 -*-

from odoo import models, fields, api


class bio_time_integration(models.Model):
    _name = 'hr.attendance.bio'
    _description = 'Bio Time ZK Integration'

    name = fields.Many2one('hr.employee', string='Employee')
    record_id = fields.Integer()
    punching_day = fields.Datetime(string='Punch Day', help="Punching Date")
    punch_time = fields.Datetime('Punch Time')
    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('25', 'Palm'),
                                        ('3', 'Password'),
                                        ('4', 'Card')],
                                       string='Category',
                                       help="Select the attendance type")
    punch_type = fields.Selection([('0', 'Check In'),
                                   ('1', 'Check Out'),
                                   ('2', 'Break Out'),
                                   ('3', 'Break In'),
                                   ('4', 'Overtime In'),
                                   ('5', 'Overtime Out')],
                                  string='Punching Type',
                                  help="Select the punch type")
    device_id = fields.Char('Device')
    seq_num = fields.Char('Sequence Number')



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    device_id = fields.Integer(string='Biometric Device ID',
                            help="Give the biometric device id")


