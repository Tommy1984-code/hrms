# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import date, timedelta
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta 



class EmployeeTermination(Document):
	 
	def validate(self):
		if self.employee and self.termination_date:
			self.generate_severance()

		self.update_final_settlement()
		self.calculate_annual_leave()

	@frappe.whitelist()
	def generate_severance(self):
		"""Generate severance table based on employee's joining date and base salary."""
		if not self.employee:
			frappe.throw("Employee is required to generate severance.")
		
		if not self.date_of_employment or not self.basic_salary:
			frappe.throw("Joining Date and Base Salary are required!!!!.")

		
		base_salary = self.basic_salary

		

		# Calculate employee and company pension
		employee_pension = base_salary * 0.07  # 7% of base salary
		company_pension = base_salary * 0.11   # 11% of base salary

		self.base_pension = round(employee_pension,2)
		self.company_pension = round(company_pension,2)

		def parse_date(date_str):
			return datetime.strptime(date_str,"%Y-%m-%d").date() if isinstance(date_str, str) else date_str
		
		joining_date = parse_date(self.date_of_employment)
		termination_date = parse_date(self.termination_date)

		existing_grants = {row.year: row.grant for row in self.severance_table}

		years_of_service = relativedelta(termination_date, joining_date).years
		if years_of_service < 5:
			frappe.msgprint("Employee must have at least 5 years of service to generate severance.")
			return 

		# Clear existing severance table if any
		self.set("severance_table", [])

		current_start_date = joining_date
		year_count = 1

		while current_start_date < termination_date:
			# Calculate next year's end date
			next_year_date = current_start_date + relativedelta(years=1) - timedelta(days=1)

			if next_year_date > termination_date:
				next_year_date = termination_date  # Ensure we don't exceed termination date

			year_duration = (next_year_date - current_start_date).days + 1
			
			if year_duration >= 365:
				percent = 1.0 if year_count == 1 else 1/3  # First year: 100%, others: 1/3
				no_of_days = (next_year_date - current_start_date).days + 1
				salary_amount = round(base_salary * percent, 2)
			else:
				percent=1/3 
				no_of_days = (next_year_date - current_start_date).days + 1
				salary_amount = round((base_salary / 3) * (year_duration / 365), 2)
				
			grant = existing_grants.get(f"{year_count} year", 0)

			# Append to severance table
			self.append("severance_table", {
				"year": f"{year_count} year",
				"date_from": current_start_date,
				"date_to": next_year_date,
				"no_of_days": no_of_days,
				"percent": round(percent * 100, 2),
				"amount": salary_amount,
				"grant": grant
			})

			# Move to the next year
			current_start_date = next_year_date + timedelta(days=1)
			year_count += 1

		

		# After generation, we also update the final severance details
		self.update_final_settlement()
		# Calculate the first part of severance tax (integer part of the rate)
		tax_rate = self.total_severance / base_salary
		
		first_severance_tax_part = int(tax_rate)
		
		remaining_fraction = round(tax_rate - first_severance_tax_part,2)  # The fractional part
		
		 # 1st part: Tax for the integer part (first_severance_tax_part)
		first_income_tax = base_salary * first_severance_tax_part
		first_tax = self.calculate_tax(first_income_tax)
		
		# 2nd part: Tax for the fractional part (remaining_fraction)
		second_tax_income = base_salary * remaining_fraction
		
		second_tax = self.calculate_tax(second_tax_income) 
         
		# Total severance taxP
		total_severance_tax = first_tax + second_tax
		# Update the total severance tax
		self.severance_tax = round(total_severance_tax, 2)

		 # Calculate net severance (gross severance - severance tax)
		net_severance = self.total_severance - self.severance_tax
		self.net_severance = round(net_severance, 2)


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

	def calculate_annual_leave(self):
		"""Calculate tax on unused annual leave compensation."""
		if not self.basic_salary or not self.worked_days or not self.annual_leave:
			return
		
		# Calculate per-day salary
		daily_salary = self.basic_salary / 26  # 26 working days per month

		# Prorate annual leave based on worked days
		eligible_leave_days = (self.annual_leave / 365) * self.worked_days

		# Calculate annual leave pay
		leave_compensation = eligible_leave_days * daily_salary

		# Calculate tax on annual leave pay
		leave_tax = self.calculate_tax(leave_compensation)

		# Calculate net leave compensation (Gross Leave Compensation - Tax)
		net_leave_compensation = leave_compensation - leave_tax

		# Store in doctype fields
		self.gross_annual_leave_payment = round(leave_compensation,2)
		self.annual_leave_tax = round(leave_tax, 2)
		self.net_annual_leave_payment = round(net_leave_compensation, 2)

	def update_final_settlement(self):
		"""Update the total severance amount in the final settlement section."""

		total = sum(row.amount for row in self.severance_table if row.grant)

		base_salary = self.basic_salary
		max_allowed_severance = base_salary * 12

		if total> max_allowed_severance:
			total = max_allowed_severance
			frappe.msgprint(f"Total severance amount exceeds the allowed limit. It has been capped to: {max_allowed_severance}")

		self.total_severance = total
		


