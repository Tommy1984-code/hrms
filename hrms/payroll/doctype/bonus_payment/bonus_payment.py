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
	def calculate_tax(self, income):
		"""Calculate the tax based on the updated Ethiopian tax system."""
		if income >= 0 and income <= 2000:
			tax = 0  # No tax for income <= 2000
		elif income > 2000 and income <= 4000:
			tax = income * 0.15 - 300
		elif income > 4000 and income <= 7000:
			tax = income * 0.20 - 500
		elif income > 7000 and income <= 10000:
			tax = income * 0.25 - 850
		elif income > 10000 and income <= 14000:
			tax = income * 0.30 - 1350
		else:  # income > 14000
			tax = income * 0.35 - 2050

		return tax

	def calculate_bonus_payment(self):
		"""Calculate Gross Bonus, Tax, and Net Bonus"""
		if not self.basic_salary:
			frappe.throw("Please set Basic Salary before calculating bonus")

		# --- Gross Bonus ---
		bonus_time_frame = (self.bonus_time_frame or "").strip()

		if bonus_time_frame == "1 Month":
			self.gross_bonus = float(self.basic_salary)
		elif bonus_time_frame == "1.5 Month":
			self.gross_bonus = float(self.basic_salary) * 1.5
		elif bonus_time_frame == "2 Month":
			self.gross_bonus = float(self.basic_salary) * 2
		elif bonus_time_frame == "3 Month":
			self.gross_bonus = float(self.basic_salary) * 3
		elif bonus_time_frame == "Other":
			if not self.days:
				frappe.throw("Please enter number of days when Bonus Timeframe is Other")
			self.gross_bonus = (float(self.days) / 26.0) * float(self.basic_salary)
		else:
			self.gross_bonus = 0

		# --- Tax Calculation ---
		# Normal monthly salary
		monthly_tax = self.calculate_tax(float(self.basic_salary))
		# Salary + 1/12 of bonus
		tax_with_bonus = self.calculate_tax((float(self.basic_salary) + (self.gross_bonus / 12)))
		# Difference * 12 → yearly impact
		self.tax_bonus = (tax_with_bonus - monthly_tax) * 12

		# --- Net Bonus ---
		self.net_bonus = self.gross_bonus - self.tax_bonus

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
		if self.gross_bonus:
			self.insert_salary_component("earnings", "Bns", self.gross_bonus)
		if self.tax_bonus:
			self.insert_salary_component("deductions", "BnsTax", self.tax_bonus)
