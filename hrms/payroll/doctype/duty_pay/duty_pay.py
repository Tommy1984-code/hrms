# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class DutyPay(Document):

	def validate(self):
		self.check_duplicate_duty_record()

	def check_duplicate_duty_record(self):
		payroll_month = getdate(self.payroll_month).strftime('%Y-%m')
		existing_record = frappe.get_value(
			'Duty Pay',
			{
				'employee': self.employee,
				'payroll_month': ['like', f'{payroll_month}%'],
				'docstatus': 1
			},
			'name'
		)
		if existing_record:
			frappe.throw(f"Duty Pay record for this employee already exists for the month: {payroll_month}.")





       