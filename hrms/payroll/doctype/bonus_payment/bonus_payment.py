import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class BonusPayment(Document):

	def validate(self):
		self.prevent_duplicate_bonus()
		self.calculate_bonus_payment()
		self.add_bonus_to_earnings()

	def prevent_duplicate_bonus(self):
		"""Prevent inserting bonus twice for the same employee in the same payroll month"""
		if self.employee and self.payroll_month:
			 # Extract year and month from payroll_month
			payroll_month = getdate(self.payroll_month).strftime('%Y-%m')  # Format: 'YYYY-MM'
			

			exists = frappe.db.exists(
				"Bonus Payment",
				{
				'employee': self.employee,
                'payroll_month': ['like', f'{payroll_month}%'],  # Check for records in the same month
                'docstatus': 1  # Only check submitted documents
				},
				'name'
			)
			if exists:
				frappe.throw(f"Bonus for employee {self.employee} already exists for {getdate(payroll_month).strftime('%B %Y')}.")


	def calculate_bonus_payment(self):
		"""Calculate the Bonus Payment of Employee"""
		if not self.basic_salary:
			frappe.throw("Please set Basic Salary before calculating bonus")

		# Formula: base / 12
		self.bonus_amount = float(self.basic_salary) / 12

	def insert_salary_component(self, table_name, component_abbr, amount):
		"""Insert or update a salary component in the specified earnings or deductions table."""

		# Get salary component name from abbreviation
		salary_component = frappe.get_value("Salary Component", {"salary_component_abbr": component_abbr}, "name")
		if not salary_component:
			frappe.throw(f"Salary Component with abbreviation '{component_abbr}' not found.")

		# Check if component already exists in the table
		found = False
		for row in self.get(table_name):
			if row.abbr == component_abbr:
				row.amount = round(amount, 2)
				found = True
				break

		# If not found, insert new row
		if not found:
			self.append(table_name, {
				"salary_component": salary_component,
				"abbr": component_abbr,
				"amount": round(amount, 2)
			})	

	def add_bonus_to_earnings(self):
		"""Add Bonus (abbr=Bns) into earnings table"""
		if self.bonus_amount:
			self.insert_salary_component("earnings", "Bns", self.bonus_amount)
