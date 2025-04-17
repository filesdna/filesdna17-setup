# -*- coding: utf-8 -*-

from odoo import models, fields, api
from lxml import etree


class EmployeeMoreDetails(models.Model):
    _inherit = 'hr.employee'

    employee_num = fields.Char("Employee Number", )  # الرقم الوظيفي للوزارة
    goverment_number = fields.Char(string='Government Number')  # الرقم الحكومي#الرقم الوطني
    first_name = fields.Char("First Name", required=True, )
    second_name = fields.Char("Second Name")
    third_name = fields.Char("Third Name")
    fourth_name = fields.Char("Fourth Name")
    fifth_name = fields.Char("Fifth Name")
    last_name = fields.Char("Last Name", required=True, )
    name = fields.Char('Full Name', compute='_compute_full_name', store=True)

    @api.onchange('first_name', 'second_name', 'third_name', 'fourth_name', 'fifth_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            names = filter(None, [
                record.first_name,
                record.second_name,
                record.third_name,
                record.fourth_name,
                record.fifth_name,
                record.last_name
            ])
            record.name = ' '.join(names)

    religion = fields.Selection(string='Religions', selection=[
        ('1', 'Islam'), ('2', 'Christianity'),
        ('3', 'Jewish')], default='1', required=True)
    nation = fields.Selection(string='Employee Nationality', required=True, selection=[
        ('1', 'arabic'), ('2', 'kurdish'), ('3', 'turkuman'), ('4', 'shabaky'),
        ('5', 'ayzidy'), ('6', 'other')])
    doctrain = fields.Selection(string='Employee Doctrain',
                                selection=[('1', 'sunni'), ('2', 'shiea'), ('3', 'other')])  # المذهب
    birth_date = fields.Date(string='Birth Date', required=True, )
    birth_gov = fields.Many2one(comodel_name='hr.employee.governorate', string='Governorate of Birth')
    mother_name = fields.Char(string='Mother Full Name', )  # اسم الام
    emp_gender = fields.Selection(string='Employee Gendar', selection=[('1', 'Male'), ('2', 'Female')], required=True, )
    # emp_status = fields.Many2one(comodel_name='hr.employee.emp_status' , string='Employee Service Status')
    # ///////////////////////////// Notional ID ////////////////////////////////////////////////////////
    national_id = fields.Char(string='National ID')
    national_issue_date = fields.Date('Issue Date')
    national_expire_date = fields.Date('Expire Date')
    national_governorate_id = fields.Many2one('hr.employee.governorate', string='State')
    # /////////////////////////////////////////////////////////////////////////
    pass_issue_date = fields.Date('Issue Date')
    pass_expire_date = fields.Date('Expire Date')
    pass_governorate_id = fields.Many2one('hr.employee.governorate', string='State')

    residence_card = fields.Char('Residence Card Number')
    residence_card_office = fields.Char('Residence Card Office Info', )
    residence_card_governorate_id = fields.Many2one('hr.employee.governorate', string='State')

    grade = fields.Many2one(comodel_name='hr.employee.grade', string='Grade')  # الدرجة
    grade_type = fields.Many2one(comodel_name='hr.employee.grade_type', string='Grade Type')
    level = fields.Many2one(comodel_name='hr.employee.level', string='Grade Step')  # المرحلة
    grade_date = fields.Date(string='Current Grade Date')
    next_grade_date = fields.Date(string='Next Grade Date')
    level_date = fields.Date(string='Current Level Date')
    next_level_date = fields.Date(string='Next Level Date')

    specialization = fields.Many2one(comodel_name='hr.employee.specialization', string='Specialization')  # التخصص
    exact_specialest = fields.Many2one(comodel_name='hr.employee.exact_specialest',
                                       string='Exact Specialest')  # التخصص الدقيق

    qual_type = fields.Selection(selection=[('1', 'Internal Governmental'),
                                            ('2', 'Internal Evening Governmental'), ('3', 'Internal Private'),
                                            ('4', 'International Governmental'),
                                            ('5', 'International Private')])  # نوع الشهادة

    certificate_id = fields.Many2one(comodel_name='hr.employee.certifiaction',
                                     string='Last Assigned Certification')
    qualification1 = fields.Many2one(comodel_name='hr.employee.certifiaction',
                                     string='First Certification')
    qualification2 = fields.Many2one(comodel_name='hr.employee.certifiaction',
                                     string='Second Certification')
    qualification3 = fields.Many2one(comodel_name='hr.employee.certifiaction',
                                     string='Third Certification')
    certification_ids = fields.Many2many(comodel_name='hr.employee.certifiaction', string='Employee Certificates')
    emp_ministry = fields.Many2one(comodel_name='hr.employee.ministry', string='Ministry')
    emp_reference_unit = fields.Many2one(comodel_name='hr.department', string='Reference Unit')
    emp_main_unit = fields.Many2one(comodel_name='hr.department', string='Main Unit')
    emp_unit = fields.Many2one(comodel_name='hr.department', string='Direct Unit')
    # transfer_from = fields.Many2one(comodel_name='hr.employee.units', string='Transferred from Unit',)#Char(string='Transfer From', ) #الجهة منقول منها
    # transfer_to = fields.Many2one(comodel_name='hr.employee.units',string='Transferred to Unit',) # الجهة منقول اليها

    # transfer_from = fields.Many2one(comodel_name='hr.employee.units', string='Transferred from Unit',ondelete='cascade')#Char(string='Transfer From', ) #الجهة منقول منها
    # transfer_to = fields.Many2one(comodel_name='hr.employee.units',string='Transferred to Unit',ondelete='cascade') # الجهة منقول اليها
    # mother_s_name = fields.Char(string='Second Name', ) #اسم الام
    # mother_t_name = fields.Char(string='Third Name',  ) #اسم الام
    # /////////////// Civilian ID INfo//////////////////////////////////////
    civilian_id = fields.Char(string='Civilian ID')
    civilian_record_number = fields.Char(string='Civilian record number')
    civilian_page_number = fields.Char(string='Civilian Page Number')
    civilian_issue_date = fields.Date('Issue Date')
    civilian_expire_date = fields.Date('Expire Date')
    civilian_governorate_id = fields.Many2one('hr.employee.governorate', string='State')

    # //////////////////////////////////////////////////////////////////////////////////////////////
    previous_marriage_state = fields.Selection([('1', 'Single'), ('2', 'Married'),
                                                ('3', 'Cohabitant'), ('4', 'Widower'), ('5', 'Divorced')], default='1',
                                               string='Previous Marriage Status')  # حالة الزواج السابقة
    service_status = fields.Many2one(comodel_name='hr.employee.emp_status', string='Employee Service Status')
    contact_id = fields.Many2one(comodel_name='hr.employee.contact',
                                 string='Contact Relation')
    job_address_id = fields.Many2one('job.address', string='Job Title')
    governorate_id = fields.Many2one('hr.employee.governorate', string='Governorate')
    city_id = fields.Many2one('hr.employee.city', string='City')
    district_id = fields.Many2one('hr.employee.district', string='District')
    address_details = fields.Char(string='Address details')
    course_list_id = fields.One2many('hr.employee.courses_list', 'employee_id', string='Employee Courses')
    delegation_list_id = fields.One2many('hr.employee.delegations_list', 'employee_id', string='Employee Delegations')
    thank_list_id = fields.One2many('hr.employee.thanks_list', 'employee_id', string='Thanks Book List')
    punishment_list_id = fields.One2many('hr.employee.punishments_list', 'employee_id', string='Punishments Book List')
    vacation_list_id = fields.One2many('hr.employee.vacations_list', 'employee_id', string='Vacations Book List')

    locked = fields.Boolean('', default=False)
    name = fields.Char('Full Name')

    # @api.model
    # def create(self, values):
    #     # Check if first_name or last_name is updated
    #     if 'first_name' in values or 'second_name' in values:
    #         first_name = values.get('first_name', self.first_name)
    #         second_name = values.get('second_name', self.second_name)
    #         # Manually update the name field
    #         values['name'] = f"{first_name} {second_name}".strip()

    #     return super(EmployeeMoreDetails, self).create(values)
    # def write(self, vals):
    #     # Add a specific string to the 'name' field when updating an employee
    #     # if 'name' in vals:
    #     vals['name'] = "Custom Prefix: " + vals['name']
    #
    #     # Call the super method to update the employee
    #     return super(EmployeeMoreDetails, self).write(vals)

    def locked(self):
        for record in self:
            record.locked = True

    @api.onchange('grade_type', 'grade', 'level')
    def set_salary(self):
        for rec in self:
            # Check if enable_basic is True
            if not rec.env["ir.config_parameter"].sudo().get_param("hr_advanced.enable_basic",
                                                                   default="False") == "True":
                return  # Exit the function if enable_basic is False
            if rec.grade_type and rec.grade and rec.level:
                basic_salary_line = self.env['hr.grade.salary.line'].search(
                    [('grade', '=', rec.grade.id), ('level', '=', rec.level.id)], limit=1)
                if basic_salary_line:
                    print('grade=', rec.grade.name)
                    print('level=', rec.level.name)
                    print('wage=', rec.contract_id.wage)
                    print('basic_salary_line=', basic_salary_line)
                    print('amount=', basic_salary_line.amount)
                    rec.contract_id.wage = basic_salary_line.amount
                else:
                    print('No salary line found for the given grade and level.')

    # -----------------------------------Merge----------------------------------------
    ministry_id = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]", string='Main')
    level_1 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_ministry_id)]")
    parent_root_ministry_id = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_ministry_id',
        store=False,
    )

    @api.depends('ministry_id')
    def _compute_parent_root_ministry_id(self):
        for record in self:
            if record.ministry_id and record.ministry_id.child_ids:
                child_ids = record.ministry_id.child_ids.ids
                record.parent_root_ministry_id = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_ministry_id = False

    level_2 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_1)]")
    parent_root_level_1 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_1',
        store=False,
    )

    @api.depends('level_1')
    def _compute_parent_root_level_1(self):
        for record in self:
            if record.level_1 and record.level_1.child_ids:
                child_ids = record.level_1.child_ids.ids
                record.parent_root_level_1 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_1 = False

    level_3 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_2)]")
    parent_root_level_2 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_2',
        store=False,
    )

    @api.depends('level_2')
    def _compute_parent_root_level_2(self):
        for record in self:
            if record.level_2 and record.level_2.child_ids:
                child_ids = record.level_2.child_ids.ids
                record.parent_root_level_2 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_2 = False

    level_4 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_3)]")
    parent_root_level_3 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_3',
        store=False,
    )

    @api.depends('level_3')
    def _compute_parent_root_level_3(self):
        for record in self:
            if record.level_3 and record.level_3.child_ids:
                child_ids = record.level_3.child_ids.ids
                record.parent_root_level_3 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_3 = False

    level_5 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_4)]")
    parent_root_level_4 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_4',
        store=False,
    )

    @api.depends('level_4')
    def _compute_parent_root_level_4(self):
        for record in self:
            if record.level_4 and record.level_4.child_ids:
                child_ids = record.level_4.child_ids.ids
                record.parent_root_level_4 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_4 = False

    level_6 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_5)]")
    parent_root_level_5 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_5',
        store=False,
    )

    @api.depends('level_5')
    def _compute_parent_root_level_5(self):
        for record in self:
            if record.level_5 and record.level_5.child_ids:
                child_ids = record.level_5.child_ids.ids
                record.parent_root_level_5 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_5 = False

    level_7 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_6)]")
    parent_root_level_6 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_6',
        store=False,
    )

    @api.depends('level_6')
    def _compute_parent_root_level_6(self):
        for record in self:
            if record.level_6 and record.level_6.child_ids:
                child_ids = record.level_6.child_ids.ids
                record.parent_root_level_6 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_6 = False

    level_8 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_7)]")
    parent_root_level_7 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_7',
        store=False,
    )

    @api.depends('level_7')
    def _compute_parent_root_level_7(self):
        for record in self:
            if record.level_7 and record.level_7.child_ids:
                child_ids = record.level_7.child_ids.ids
                record.parent_root_level_7 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_7 = False

    level_9 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_8)]")
    parent_root_level_8 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_8',
        store=False,
    )

    @api.depends('level_8')
    def _compute_parent_root_level_8(self):
        for record in self:
            if record.level_8 and record.level_8.child_ids:
                child_ids = record.level_8.child_ids.ids
                record.parent_root_level_8 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_8 = False

    level_10 = fields.Many2one('hr.department', domain="[('id', 'in', parent_root_level_9)]")
    parent_root_level_9 = fields.Many2many(
        'hr.department',
        compute='_compute_parent_root_level_9',
        store=False,
    )

    @api.depends('level_9')
    def _compute_parent_root_level_9(self):
        for record in self:
            if record.level_9 and record.level_9.child_ids:
                child_ids = record.level_9.child_ids.ids
                record.parent_root_level_9 = self.env['hr.department'].search(
                    [('id', 'in', child_ids)]
                )
            else:
                record.parent_root_level_9 = False

    # directorate_id = fields.Many2one('hr.department', domain="[('parent_id', '=', office_id)]")
    # section_id = fields.Many2one('hr.department',
    #                              domain="[('parent_id', '=', directorate_id),('parent_root', '=', ministry_id), ('level', '=', 6)]")
    # department_id = fields.Many2one(compute='_compute_unit_number')
    root_unit_id = fields.Char(compute='_compute_unit_number')
    unit_id = fields.Char(compute='_compute_unit_number')

    @api.onchange('level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6', 'level_7', 'level_8', 'level_9',
                  'level_10')
    def _onchange_level(self):
        for record in self:
            for level in range(10, 0, -1):
                level_field = f'level_{level}'
                if getattr(record, level_field):
                    record.department_id = getattr(record, level_field).id
                    break

    @api.onchange('department_id')
    def _compute_unit_number(self):
        for record in self:
            record.unit_id = ''
            record.root_unit_id = ''
            record.department_id = ''

            for level in range(10, 0, -1):
                level_field = f'level_{level}'  # search from 10 to 0 and stop at last level you add it
                print('level_field=', level_field)
                if getattr(record, level_field):  # check if level_field is empty value or no
                    record.unit_id = getattr(record, level_field).number
                    record.root_unit_id = getattr(record, level_field).parent_id.number
                    record.department_id = getattr(record, level_field).id
                    break

    # Box File
    files_count = fields.Integer(
        string='Files', compute='_compute_count_files'
    )

    def _compute_count_files(self):
        for record in self:
            config_param = self.env["ir.config_parameter"].sudo()
            enable_document_tags_filtering = config_param.get_param("dms.enable_document_tags_filtering",
                                                                    default="True") == "True"
            filter_tags_str = config_param.get_param("dms.filter_tags", default="")
            if enable_document_tags_filtering and filter_tags_str:
                filter_tags_list = [tag.strip() for tag in filter_tags_str.split(',')] if filter_tags_str else []
                file_employee_count = self.env['dms.file'].search_count([
                    ('create_uid', '=', record.user_id.id),
                    ('tag_ids.name', 'in', filter_tags_list),
                ])
                record.files_count = file_employee_count
            else:
                file_employee_count = self.env['dms.file'].search_count([
                    ('create_uid', '=', record.user_id.id),
                ])
                record.files_count = file_employee_count
    # --------------------------------------------------------------------------------


class HrEmployeeGrade(models.Model):
    _name = 'hr.employee.grade'
    _description = 'Employees Grades'

    name = fields.Char(string='Name')
    code = fields.Integer(string='Code')
    steps_count = fields.Integer(string='Grade Steps Count')
    grade_type = fields.Many2one(comodel_name='hr.employee.grade_type', string='Grade Type')
    years_count = fields.Integer(string='Number Of Years to Upgrade')
    required_course = fields.Many2one(comodel_name='hr.employee.course', string='Required Course')
    requre_approve = fields.Boolean(string='Requre Managers Approvement')


class HrEmployeeCourse(models.Model):
    _name = 'hr.employee.course'
    _description = 'Course'

    name = fields.Char(string='Course Name', required=True, )
    course_type = fields.Selection(selection=[('1', 'ضمن المؤسسة'), ('2', 'داخل البلاد'), ('3', 'خارج البلاد')]
                                   , string='Course Type')
    course_duration = fields.Integer(string='Course Duration')
    is_certified = fields.Boolean(string='Is Certified')
    course_level = fields.Integer(string='Course Level')
    participater_limit_count = fields.Integer(string='Max Allowed Participators')
    is_free = fields.Boolean(string='Is Free')
    course_amount = fields.Integer(string='Course Amount/Participater')
    course_notes = fields.Char(string='Notes')


class EmployeeCoursesList(models.Model):
    _name = 'hr.employee.courses_list'
    _description = 'Courses List'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    course_id = fields.Many2one(comodel_name='hr.employee.course', string='Courses')
    course_start_date = fields.Date(string='Start Date')
    course_end_date = fields.Date(string='End Date')
    order_book_no = fields.Char(string='Book Number')
    order_book_date = fields.Date(string='Book Date')
    participator_count = fields.Integer(string='Number Of Participators')
    employee_seq = fields.Integer(string='Employee Sequence')
    employee_status = fields.Selection(
        selection=[('1', 'امتياز'), ('2', 'جيد جدا'), ('3', 'جيد'), ('4', 'مقبول'), ('5', 'ضعيف')],
        string='Employee Result')
    notes = fields.Char(string='Course Notes')


class HrEmployeeDelegation(models.Model):
    _name = 'hr.employee.delegation'
    _description = 'Delegation'

    name = fields.Char(string='Delegation Name', required=True, )
    delegation_type = fields.Selection(selection=[('1', 'ضمن المؤسسة'), ('2', 'داخل البلاد'), ('3', 'خارج البلاد')]
                                       , string='Delegation Type')
    delegation_duration = fields.Integer(string='Delegation Duration')
    is_free = fields.Boolean(string='Is Free')
    delegation_amount = fields.Integer(string='Delegation Amount/Participater')
    delegation_notes = fields.Char(string='Notes')


class EmployeeDelegationsList(models.Model):
    _name = 'hr.employee.delegations_list'
    _description = 'Delegations List'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    delegation_id = fields.Many2one(comodel_name='hr.employee.delegation', string='Delegation')
    delegation_start_date = fields.Date(string='Start Date')
    delegation_end_date = fields.Date(string='End Date')
    order_book_no = fields.Char(string='Book Number')
    order_book_date = fields.Date(string='Book Date')
    participator_count = fields.Integer(string='Number Of Participators')
    notes = fields.Char(string='Delegation Notes')


class HrEmployeeThanks(models.Model):
    _name = 'hr.employee.thank'
    _description = 'Thank'

    name = fields.Char(string='Thank Name', required=True, )
    serving_month_count = fields.Integer(string='Serving Months Count')


class EmployeeThsnksList(models.Model):
    _name = 'hr.employee.thanks_list'
    _description = 'Thanks List'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    thank_id = fields.Many2one(comodel_name='hr.employee.thank', string='Thanks')
    thank_book_no = fields.Char(string='Book Number')
    thank_book_date = fields.Date(string='Book Date')
    is_used = fields.Boolean(string='Is Used')
    notes = fields.Char(string='Thank Notes')


class HrEmployeePunishments(models.Model):
    _name = 'hr.employee.punishment'
    _description = 'Punishment'

    name = fields.Char(string='Punishmen Name', required=True, )
    serving_month_count = fields.Integer(string='Serving Months Count')


class EmployeePunishmenstList(models.Model):
    _name = 'hr.employee.punishments_list'
    _description = 'Punishments List'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    punishment_id = fields.Many2one(comodel_name='hr.employee.punishment', string='Punishment')
    punishment_book_no = fields.Char(string='Book Number')
    punishment_book_date = fields.Date(string='Book Date')
    is_used = fields.Boolean(string='Is Used')
    notes = fields.Char(string='Punishment Notes')


class HrEmployeeVacation(models.Model):
    _name = 'hr.employee.vacation'
    _description = 'Vacation'

    name = fields.Char(string='Vacation Name', required=True, )
    duration_type = fields.Selection(string='Duration Type', selection=[('1', 'يوم'), ('2', 'شهر')])
    vacation_duration = fields.Integer(string='Vacation Duration(day)')
    effect_balance = fields.Boolean(string='Effect On Vacation Balance')
    require_approve = fields.Boolean(string='Require Approve')
    is_yearly = fields.Boolean(string='Is Yearly')
    year_count = fields.Integer(string='Year Count')
    is_monthly = fields.Boolean(string=' Is Monthly')
    month_count = fields.Integer(string='Month Count')


class EmployeeVacationList(models.Model):
    _name = 'hr.employee.vacations_list'
    _description = 'Vacations List'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    vacation_id = fields.Many2one(comodel_name='hr.employee.vacation', string='Vacation')
    vacation_date = fields.Date(string='Vacation Date')
    vacation_book_no = fields.Char(string='Book Number')
    vacation_book_date = fields.Date(string='Book Date')
    is_used = fields.Boolean(string='Is Used')
    notes = fields.Char(string='Vacation Notes')


class HrEmployeeGradeTypes(models.Model):
    _name = 'hr.employee.grade_type'
    _description = 'Employees Grades Type'

    name = fields.Char(string='Name')
    code = fields.Integer(string='Code')


class HrEmployeeLevel(models.Model):
    _name = 'hr.employee.level'
    _description = 'Employees levels'

    name = fields.Char(string='Name', )
    grade_type = fields.Many2one(comodel_name='hr.employee.grade_type', string='Level Grade Tyoe')
    years_count = fields.Float(string='Level years count')
    requre_approve = fields.Boolean(string='Require Managers Approvement')


class HrEmployeeSpecialization(models.Model):
    _name = 'hr.employee.specialization'
    _description = 'Employees specializations'

    name = fields.Char(string='Name', )


class HrEmployeeExactSpecialization(models.Model):
    _name = 'hr.employee.exact_specialest'
    _description = 'Employees Exact Spetialest'

    name = fields.Char(string='Name', )


class EmployeeContactRelation(models.Model):
    _name = 'hr.employee.contact'

    name = fields.Char(string='Relation', )


class EmployeeState(models.Model):
    _name = 'hr.employee.governorate'

    name = fields.Char(string='Governorate(State)', )
    # city_id=fields.Many2one(comodel_name='hr.employee.city',string='City')


class EmployeeServiceStatus(models.Model):
    _name = 'hr.employee.emp_status'

    name = fields.Char(string='Service Status', )


class EmployeeMinistry(models.Model):
    _name = 'hr.employee.ministry'

    name = fields.Char(string='Ministry Name', )


class EmployeeOfficesCustom(models.Model):
    _inherit = 'hr.department'

    # ministry = fields.Many2one(comodel_name='hr.employee.ministry', string='Ministry')
    # unit_level = fields.Integer(string='Unit Level')
    # ref_unit = fields.Many2one(comodel_name='hr.department', string='Reference Unit')
    # main_unit = fields.Many2one(comodel_name='hr.department', string='Main Unit')
    # parent_unit = fields.Many2one(comodel_name='hr.department', string='Parent Unit')
    # is_main = fields.Boolean('', default=False)
    # unit_address = fields.Char(string='Unit Address')
    # unit_manager = fields.Many2one(comodel_name='hr.employee', string='Manager Name')
    # unit_manager_assistant = fields.Many2one(comodel_name='hr.employee', string='Debuty Manager')
    # ------------------Merge-----------------------------------------------------------------------
    number = fields.Char()
    deputy = fields.Many2one('hr.employee')
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    level = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
    ])
    parent_root = fields.Many2one('hr.department', domain="[('parent_id', '=', False)]")
    # -----------------------------------------------------------------------------------
    name = fields.Char(required=True, translate=True)
    root_parent = fields.Many2one('hr.department', domain="[('level', '=', 2)]")
    main_parent = fields.Many2one('hr.department')
    parent_id = fields.Many2one('hr.department', index=True, check_company=True)
    parent_id_new = fields.Many2one('hr.department', domain="[('level', '=', 2)]")
    top_formation = fields.Boolean()

    @api.onchange('top_formation')
    def _onchange_top_formation(self):
        for rec in self:
            if rec.top_formation:
                print('hhh')

    def _set_parent_root(self, department):
        if department.parent_id:
            department.parent_root = department.parent_id.parent_root or department.parent_id
        else:
            department.parent_root = department.complete_name

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = department.name
            else:
                department.complete_name = department.name

    @api.model
    def create(self, vals):
        res = super(EmployeeOfficesCustom, self).create(vals)
        if res.parent_id:
            res.parent_root = res.parent_id.parent_root or res.parent_id

        # if res.parent_id and res.parent_id.is_section:
        #     res.is_department = True

        return res

    def write(self, vals):
        if 'parent_id' in vals:
            for record in self:
                if vals['parent_id']:
                    parent_department = self.browse(vals['parent_id'])
                    record.parent_root = parent_department.parent_root or parent_department
                else:
                    record.parent_root = False
        return super(EmployeeOfficesCustom, self).write(vals)

    # ----------------------------------------------------------------------------------------------


class EmployeeUnits(models.Model):
    _name = 'hr.employee.units'

    name = fields.Char(string='Unit Name', )
    ministry = fields.Many2one(comodel_name='hr.employee.ministry', string='Ministry')
    unit_level = fields.Integer(string='Unit Level')
    ref_unit = fields.Many2one(comodel_name='hr.employee.units', string='Reference Unit')
    main_unit = fields.Many2one(comodel_name='hr.employee.units', string='Main Unit')
    parent_unit = fields.Many2one(comodel_name='hr.employee.units', string='Parent Unit')
    is_main = fields.Boolean('', default=False)
    unit_address = fields.Char(string='Unit Address')
    unit_manager = fields.Many2one(comodel_name='hr.employee', string='Manager Name')
    unit_manager_assistant = fields.Many2one(comodel_name='hr.employee', string='Debuty Manager')


class EmployeePosition(models.Model):
    _name = 'hr.employee.position'
    _description = 'Employee Position'

    name = fields.Char(string='Employee Position', required=True, )
    percent_amount = fields.Integer(string='Percent Salary Amount %')
    fixed_amount = fields.Float(string='Fixed Salary Amount')
    grade_type = fields.Many2one(comodel_name='hr.employee.grade_type', string='Grade Type')
    min_grade = fields.Many2one(comodel_name='hr.employee.grade', string='Minimum Allowed Grade')
    max_grade = fields.Many2one(comodel_name='hr.employee.grade', string='Maximum Allowed Grade')
    position_level = fields.Integer(string='Position Level')
    main_job_details = fields.Char(string='Main Job Of Position')
    second_job_details = fields.Char(string='Second Job Of Position')
    min_qual = fields.Many2one(comodel_name='hr.employee.certifiaction', string='Minimum Qualification')
    pos_job_title_id = fields.Many2one(comodel_name='hr.employee.pos_job_title', string='Position Job Title')
    position_class = fields.Many2one(comodel_name='hr.employee.class_emp', string='Class')
    max_disability_percent = fields.Integer(string='Max Allowed Disability %')
    required_previous_pos = fields.Many2one(comodel_name='hr.employee.position')
    max_allowed_years = fields.Integer('Max Allowed Occupation Years')
    required_course = fields.Many2one(comodel_name='hr.employee.course', string='Required Course')
    require_manager_approve = fields.Boolean('', defualt=False)


class EmployeeJobTitle(models.Model):
    _name = 'hr.employee.pos_job_title'
    _description = 'Job Title'

    name = fields.Char(string='Job Title', required=True, )
    allowed_grade_type = fields.Many2one(comodel_name='hr.employee.grade_type', string='Grade Type')
    allowed_grade = fields.Many2one(comodel_name='hr.employee.grade', string='Grade')
    min_qual = fields.Many2one(comodel_name='hr.employee.certifiaction')
    percent_amount = fields.Integer(string='Percent Salary Amount %')
    fixed_amount = fields.Float(string='Fixed Salary Amount')


class EmployeeClass(models.Model):
    _name = 'hr.employee.class_emp'
    _description = 'Employee Class'

    name = fields.Char(string='Employee Class', required=True, )
    min_qual = fields.Many2one(comodel_name='hr.employee.certifiaction')
    percent_amount = fields.Integer(string='Percent Salary Amount %')
    fixed_amount = fields.Float(string='Fixed Salary Amount')


class EmployeeState(models.Model):
    _name = 'hr.employee.certifiaction'

    name = fields.Char(string='Certification', )
    certification_level = fields.Integer(string='Certification Level')
    percentage = fields.Float(string='Percentage Salary Amount')
    fixed_amount = fields.Float(string='Fixed Salary Amount')


class EmployeeCities(models.Model):
    _name = 'hr.employee.city'

    name = fields.Char(string='City', )
    city_code = fields.Integer(string='City Code')
    # district_id = fields.Many2one(comodel_name='hr.employee.district',string='District')
    gov_id = fields.Many2one(comodel_name='hr.employee.governorate', string='Governorate')


class EmployeeDistricts(models.Model):
    _name = 'hr.employee.district'

    name = fields.Char(string='District', )
    district_code = fields.Integer(string='District Code')
    gov_id = fields.Many2one(comodel_name='hr.employee.governorate', string='Governorate')
    city_id = fields.Many2one(comodel_name='hr.employee.city', string='City')


class EmployeeUniversity(models.Model):
    _name = 'hr.employee.university'

    name = fields.Char(string='University', )
    university_code = fields.Integer(string='University Code')
    university_type = fields.Selection(selection=[('1', 'داخلي حكومي صباحي'), ('2', 'داخلي حكومي مسائي'),
                                                  ('3', 'داخلي اهلي'), ('4', 'خارجي حكومي'), ('5', 'خارجي اهلي')],
                                       string='University Type')


class EmployeeColleges(models.Model):
    _name = 'hr.employee.college'

    name = fields.Char(string='College', )
    college_code = fields.Integer(string='College Code')
    university_id = fields.Many2one(comodel_name='hr.employee.university', string='University')


class EmployeeCollegeDepts(models.Model):
    _name = 'hr.employee.college_dept'

    name = fields.Char(string='Department', )
    department_code = fields.Integer(string='Department Code')
    college_id = fields.Many2one(comodel_name='hr.employee.college', string='College')
