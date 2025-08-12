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

		# Clear the earnings and deductions table before inserting new rows
		self.clear_salary_component_tables()

		# Insert Severance Gross into earnings_table
		if self.total_severance:
			self.insert_salary_component("earnings", "sevr", self.total_severance)

		# Insert Severance Tax into deductions_table
		if self.severance_tax:
			self.insert_salary_component("deductions", "sevrinc", self.severance_tax)


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

	def calculate_annual_leave(self):
		"""Calculate annual leave compensation and tax, prorated by worked days."""
		if not self.basic_salary or not self.annual_leave:
			return
		
		dates = frappe.db.get_value("Employee",
							self.employee, ["date_of_joining", "relieving_date"], as_dict=True)
		if not dates or not dates.date_of_joining or not dates.relieving_date:
			frappe.throw("Employee joining date or relieving date is missing.")

		date_of_joining = dates.date_of_joining
		relieving_date = dates.relieving_date

		# Convert to datetime if not already
		if not isinstance(date_of_joining, datetime):
			start_date = datetime.strptime(str(date_of_joining), "%Y-%m-%d")
		else:
			start_date = date_of_joining

		if not isinstance(relieving_date, datetime):
			end_date = datetime.strptime(str(relieving_date), "%Y-%m-%d")
		else:
			end_date = relieving_date

		# Calculate worked days capped at 365
		worked_days = (end_date - start_date).days + 1
		self.worked_days = min(worked_days, 365)
		

		# Step 2: Calculate per-day salary from monthly base
		daily_salary = self.basic_salary / 26

		# Step 3: Prorate eligible leave days if worked less than 365
		eligible_leave_days = (self.annual_leave / 365) * self.worked_days

		# Step 4: Calculate Gross Leave Payment
		gross_annual_leave_payment = eligible_leave_days * daily_salary

		# Step 5: Monthly leave compensation (used for tax adjustment)
		monthly_leave_compensation = gross_annual_leave_payment / 12

		# Step 6: Base tax on normal salary
		base_salary_tax = self.calculate_tax(self.basic_salary)

		# Step 7: Tax on (base + monthly leave)
		combined_tax = self.calculate_tax(self.basic_salary + monthly_leave_compensation)

		# Step 8: Difference in tax per month
		monthly_tax_difference = combined_tax - base_salary_tax

		# Step 9: Annual leave tax = monthly diff * 12
		annual_leave_tax = monthly_tax_difference * 12

		# Step 10: Net leave = gross - tax
		net_annual_leave_payment = gross_annual_leave_payment - annual_leave_tax

		# Step 11: Save values to the document
		self.gross_annual_leave_payment = round(gross_annual_leave_payment, 2)
		self.annual_leave_tax = round(annual_leave_tax, 2)
		self.net_annual_leave_payment = round(net_annual_leave_payment, 2)

		# Step 12: Insert into earnings and deductions tables
		if self.gross_annual_leave_payment:
			self.insert_salary_component("earnings", "annlev", self.gross_annual_leave_payment)

		if self.annual_leave_tax:
			self.insert_salary_component("deductions", "annlevtax", self.annual_leave_tax)

	def update_final_settlement(self):
		"""Update the total severance amount in the final settlement section."""

		total = sum(row.amount for row in self.severance_table if row.grant)

		base_salary = self.basic_salary
		max_allowed_severance = base_salary * 12

		if total> max_allowed_severance:
			total = max_allowed_severance
			frappe.msgprint(f"Total severance amount exceeds the allowed limit. It has been capped to: {max_allowed_severance}")

		self.total_severance = total
		
	def clear_salary_component_tables(self):
		"""Clear previous entries in earnings and deductions tables."""
		self.set("earnings", [])
		self.set("deductions", [])

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


		


