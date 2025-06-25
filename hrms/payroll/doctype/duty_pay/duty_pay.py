# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class DutyPay(Document):

	def validate(self):
		self.check_duplicate_duty_record()
		self.calculate_duty_pay()

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

	def calculate_tax(self, income):
		"""Calculate the tax based on the Ethiopian tax system."""
		if income >= 0 and income <= 600:
			tax = income * 0
		elif income > 600 and income <= 1650:
			tax = income * 0.10 - 60
		elif income > 1650 and income <= 3200:
			tax = income * 0.15 - 142.5
		elif income > 3200 and income <= 5250:
			tax = income * 0.20 - 302.5
		elif income > 5250 and income <= 7800:
			tax = income * 0.25 - 565
		elif income > 7800 and income <= 10900:
			tax = income * 0.30 - 955
		else:
			tax = income * 0.35 - 1500
		return round(tax, 2)

	def calculate_duty_pay(self):
		"""Calculate gross and tax from net (duty amount), and insert salary components."""
		if not self.amount:
			return

		net = self.amount
		gross = 0
		tax = 0

		# Reverse logic
		if net <= 600:
			gross = net
			tax = 0
		elif (g := (net - 60) / 0.9) <= 1650:
			gross = g
		elif (g := (net - 142.5) / 0.85) <= 3200:
			gross = g
		elif (g := (net - 302.5) / 0.8) <= 5250:
			gross = g
		elif (g := (net - 565) / 0.75) <= 7800:
			gross = g
		elif (g := (net - 955) / 0.7) <= 10900:
			gross = g
		else:
			gross = (net - 1500) / 0.65

		tax = self.calculate_tax(gross)
		gross = round(gross, 2)
		net_check = round(gross - tax, 2)

		# Optional: verify closeness
		if abs(net_check - net) > 1:
			frappe.throw(f"Unable to compute accurate gross. Got: {net_check}, expected: {net}")

		# Save to fields (optional)
		self.gross_duty = gross
		self.duty_tax = tax

		# Clear previous rows
		self.clear_salary_component_tables()

		# Insert salary components
		self.insert_salary_component("earnings", "DG", gross)
		self.insert_salary_component("deductions", "DIT", tax)

	def clear_salary_component_tables(self):
		"""Clear previous entries in earnings and deductions tables."""
		self.set("earnings", [])
		self.set("deductions", [])

	def insert_salary_component(self, table_name, component_abbr, amount):
		"""Insert or update a salary component in the specified earnings or deductions table."""
		salary_component = frappe.get_value("Salary Component", {"salary_component_abbr": component_abbr}, "name")
		if not salary_component:
			frappe.throw(f"Salary Component with abbreviation '{component_abbr}' not found.")

		found = False
		for row in self.get(table_name):
			if row.abbr == component_abbr:
				row.amount = round(amount, 2)
				found = True
				break

		if not found:
			self.append(table_name, {
				"salary_component": salary_component,
				"abbr": component_abbr,
				"amount": round(amount, 2)
			})

       