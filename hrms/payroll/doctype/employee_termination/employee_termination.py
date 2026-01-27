# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import date, timedelta
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta 
import calendar



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

		self.base_pension = round(employee_pension, 2)
		self.company_pension = round(company_pension, 2)

		def parse_date(date_str):
			return datetime.strptime(date_str, "%Y-%m-%d").date() if isinstance(date_str, str) else date_str
		
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
			next_year_date = current_start_date + relativedelta(years=1) - timedelta(days=1)

			if next_year_date > termination_date:
				next_year_date = termination_date  # Ensure we don't exceed termination date

			days_diff = (next_year_date - current_start_date).days

			# If full year (365 days counting inclusive), add +1 day
			if days_diff >= 364:
				year_duration = days_diff + 1
				percent = 1.0 if year_count == 1 else 1/3
				salary_amount = round(base_salary * percent, 2)
			else:
				# Partial last year: do NOT add +1 day
				year_duration = days_diff
				percent = 1/3
				salary_amount = round((base_salary / 3) * (year_duration / 365), 2)

			grant = existing_grants.get(f"{year_count} year", 0)

			self.append("severance_table", {
				"year": f"{year_count} year",
				"date_from": current_start_date,
				"date_to": next_year_date,
				"no_of_days": year_duration,
				"percent": round(percent * 100, 2),
				"amount": salary_amount,
				"grant": grant
			})

			current_start_date = next_year_date + timedelta(days=1)
			year_count += 1

		# After generation, update final severance details
		self.update_final_settlement()

		# Determine how many full base-salary multiples there are
		tax_rate = self.total_severance / base_salary

		full_units = int(tax_rate)  # full base salary multiples
		fraction_units = tax_rate - full_units  # decimal remainder

		# First part: tax for the full multiples
		first_tax = 0
		if full_units > 0:
			first_tax_income = base_salary  # tax base salary once
			first_tax = self.calculate_tax(first_tax_income) * full_units

		# Second part: tax for the fractional remainder
		second_tax = 0
		if fraction_units > 0:
			second_tax_income = base_salary * fraction_units
			second_tax = self.calculate_tax(second_tax_income)

		# Total severance tax
		total_severance_tax = first_tax + second_tax
		self.severance_tax = round(total_severance_tax, 2)

		# Net severance
		net_severance = self.total_severance - self.severance_tax
		self.net_severance = round(net_severance, 2)


		self.clear_salary_component_tables()

		if self.total_severance:
			self.insert_salary_component("earnings", "sevr", self.total_severance)

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
		"""Calculate annual leave compensation and tax accurately using worked days (limited to 1 year)."""

		if not self.basic_salary or not self.annual_leave:
			return

		# Fetch employee dates
		dates = frappe.db.get_value(
			"Employee",
			self.employee,
			["date_of_joining", "relieving_date"],
			as_dict=True
		)

		if not dates or not dates.date_of_joining or not dates.relieving_date:
			frappe.throw("Employee joining date or relieving date is missing.")

		start_date = (
			dates.date_of_joining
			if isinstance(dates.date_of_joining, datetime)
			else datetime.strptime(str(dates.date_of_joining), "%Y-%m-%d")
		)

		end_date = (
			dates.relieving_date
			if isinstance(dates.relieving_date, datetime)
			else datetime.strptime(str(dates.relieving_date), "%Y-%m-%d")
		)

		# Step 1: Calculate actual worked days
		total_worked_days = (end_date - start_date).days + 1
		# Step 2: Limit to 1 year for annual leave calculation
		worked_days = min(total_worked_days, 366 if calendar.isleap(start_date.year) else 365)
		self.worked_days = worked_days 

		# Step 3: Daily salary (26 working days per month)
		daily_salary = self.basic_salary / 26

		# Step 4: Gross annual leave (based on leave days)
		gross_annual_leave_payment = self.annual_leave * daily_salary

		# Step 5: Tax calculation using day-based approach
		# Tax on base salary
		base_tax = self.calculate_tax(self.basic_salary)
		# Tax on base + leave
		combined_tax = self.calculate_tax(self.basic_salary + gross_annual_leave_payment)
		# Annual leave tax = difference
		annual_leave_tax = max(combined_tax - base_tax, 0)

		# Step 6: Net leave payment
		net_annual_leave_payment = gross_annual_leave_payment - annual_leave_tax

		# Step 7: Save values
		self.gross_annual_leave_payment = round(gross_annual_leave_payment, 2)
		# self.annual_leave_tax = round(annual_leave_tax, 2)
		# self.net_annual_leave_payment = round(net_annual_leave_payment, 2)

		# Step 8: Insert salary components
		if self.gross_annual_leave_payment:
			self.insert_salary_component(
				"earnings", "annlev", self.gross_annual_leave_payment
			)

		# if self.annual_leave_tax:
		# 	self.insert_salary_component(
		# 		"deductions", "annlevtax", self.annual_leave_tax
		# 	)

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


		


