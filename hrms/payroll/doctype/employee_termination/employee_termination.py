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

	@frappe.whitelist()
	def generate_severance(self):
		"""Generate severance table based on employee's joining date and base salary."""
		if not self.employee:
			frappe.throw("Employee is required to generate severance.")
		
		# employee = frappe.get_doc("Employee", self.employee)

		date_of_joining, basic_salary = frappe.db.get_value(
        "Employee", self.employee, ["date_of_joining", "base"]
    )

		# if not date_of_joining or not basic_salary:
		# 	frappe.throw("Joining Date and Base Salary are required to calculate severance.")

		if not self.date_of_employment or not self.basic_salary:
			frappe.throw("Joining Date and Base Salary are required to calculate severance.")

		
		base_salary = self.basic_salary

		# Calculate employee and company pension
		employee_pension = base_salary * 0.07  # 7% of base salary
		company_pension = base_salary * 0.11   # 11% of base salary

		self.base_pension = round(employee_pension,2)
		self.company_pension = round(company_pension,2)

		if isinstance(self.date_of_employment,str):
			joining_date = datetime.strptime(self.date_of_employment,"%Y-%m-%d").date()
		else:
			joining_date = self.date_of_employment

		if isinstance(self.termination_date, str):
			termination_date = datetime.strptime(self.termination_date, "%Y-%m-%d").date()
		else:
			termination_date = self.termination_date

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

			year_duration = (next_year_date - current_start_date).days

			if year_duration < 364:
				current_start_date = next_year_date + timedelta(days=1)
				year_count += 1
				continue
			

			percent = 1.0 if year_count == 1 else 1/3  # First year: 100%, others: 1/3
			no_of_days = (next_year_date - current_start_date).days + 1
			salary_amount = round(base_salary * percent, 2)

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
		

	def update_final_settlement(self):
		"""Update the total severance amount in the final settlement section."""
		total = sum(row.amount for row in self.severance_table if row.grant)
		self.total_severance = total
		


