# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _  # Import translation function



class AnnualLeave(Document):
	
	def validate(self):
		self.check_duplicate_annual_leave()
		self.calculate_gross_annual_leave()
		self.calculate_annual_leave_tax()
		self.calculate_net_annual_leave()

	def check_duplicate_annual_leave(self):
		"""Ensure an employee does not have more than one Annual Leave entry in the same year."""
		posting_year = self.posting_date[:4]  # Extract only the year part (YYYY)

		existing_annual_leave = frappe.db.exists(
			"Annual Leave",
			{
				"employee": self.employee,
				"posting_date": ["between", [f"{posting_year}-01-01", f"{posting_year}-12-31"]],
				"name": ["!=", self.name]  # Exclude current document for updates
			}
		)

		if existing_annual_leave:
			frappe.throw(_("Annual Leave has already been calculated for this employee in {0}. You cannot create it twice.").format(posting_year))


	def calculate_gross_annual_leave(self):
		"""Calculate Gross Annual Leave"""
		if self.base_salary and self.annual_leave_days: 
			self.gross_annual_leave = (self.base_salary / 26) * self.annual_leave_days
		else:
			self.gross_annual_leave = 0

	def calculate_annual_leave_tax(self):
		"""Calculate Annual Leave Tax"""
		if self.gross_annual_leave:
			monthly_equivalent = self.gross_annual_leave / 12  # Convert annual leave to monthly value
			total_monthly_income = self.base_salary + monthly_equivalent
			
			# Apply tax function for total taxable income
			total_monthly_tax = self.calculate_tax(total_monthly_income)
			
			# Apply tax function for basic salary
			base_salary_tax = self.calculate_tax(self.base_salary)
			
			# Annual leave tax per month
			annual_leave_tax_per_month = total_monthly_tax - base_salary_tax
			
			# Annual leave tax for 12 months
			self.annual_leave_tax = annual_leave_tax_per_month * 12 
		else:
			self.annual_leave_tax = 0

	def calculate_net_annual_leave(self):
		"""Calculate Net Annual Leave Payment"""
		if self.gross_annual_leave and self.annual_leave_tax:
			self.net_annual_leave = self.gross_annual_leave - self.annual_leave_tax
		else:
			self.net_annual_leave = 0 

	def calculate_tax(self,income):
		"""Calculate the tax based on the Ethiopian tax system, using a simplified approach."""
		if income >= 0 and income <= 600:
			tax = income * 0  # No tax for income <= 600
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
		else:  # income > 10900
			tax = income * 0.35 - 1500

		return tax
