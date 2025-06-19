# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import today
import frappe


class LoanManagement(Document):

	def before_save(self):
		self.add_loan_salary_component()
	
	def validate(self):
		self.check_duplicate_load_type()
		self.validate_monthly_deduction()
		self.validate_loan_paid_amount()
		self.update_remaining_amount()
		
		# self.add_loan_salary_component()
		if self.loan_paid:
			self.loan_paid = 0


	def check_duplicate_load_type(self):
		"""check for duplicate loan types for the same employee"""
		if self.loan_type and self.employee:
			duplicate_loans = frappe.get_all('Loan Management',
									filters={
										"employee":self.employee,
										"loan_type":self.loan_type,
										'name':['!=',self.name] #Exclude current document if editing

									})
			if duplicate_loans:
				frappe.throw(f"Employee {self.employee} already has a loan of type '{self.loan_type}'.")
	
	def add_loan_salary_component(self):
		"""Update the 'Loan' salary component inside the Loan Management doctype's child table (Deductions)."""

		# Assume loan_type is the Salary Component name directly
		loan_component = self.loan_type  # This is a Link field to Salary Component

		# Make sure it's a valid loan component
		is_loan_component = frappe.get_value("Salary Component", loan_component, "loan_component")
		if not is_loan_component:
			frappe.msgprint(f"Selected Salary Component '{loan_component}' is not marked as a loan component.")
			return

		# Fetch the selected loan component from Salary Component
		loan_component_name = frappe.get_value("Salary Component", {"name": loan_component}, ["name","salary_component_abbr"])
		if not loan_component_name:
			return  # Exit if no corresponding salary component exists

		# Fetch the latest remaining loan balance and monthly deduction
		latest_remaining_amount = self.remaining_amount
		latest_monthly_deduction = self.monthly_deduction

		if latest_remaining_amount <= 0:
			return  # Exit if loan has been fully repaid

		adjusted_deduction = min(latest_monthly_deduction, latest_remaining_amount)

		# Get the first (and only) existing deduction entry
		existing_entry = self.get("deductions")[0] if self.get("deductions") else None

		if existing_entry:
			existing_entry.amount = adjusted_deduction  # Update existing deduction
		else:
			self.append("deductions", {
				"salary_component": loan_component_name[0],
				"abbr": loan_component_name[1],
				"amount": adjusted_deduction
			})

		frappe.db.commit()

	


	def validate_monthly_deduction(self):
		"""Ensure that monthly deduction does not exceed the loan amount."""
		if self.monthly_deduction and self.monthly_deduction > self.loan_amount:
			frappe.throw("Monthly deduction cannot exceed the loan amount.")

	def validate_loan_paid_amount(self):
		"""Ensure that loan paid amount does not exceed the remaining balance."""
		remaining_amount = self.remaining_amount or 0 
		if self.loan_paid > self.loan_amount:
			frappe.throw("Loan paid amount cannot exceed the total loan amount.")
		if self.loan_paid > remaining_amount:
			frappe.throw("Loan paid amount cannot exceed the remaining loan balance.")


	def validate_remaining_balance(self):
		"""Ensure the remaining loan balance is not negative."""
		total_paid = sum(entry.paid_amount for entry in self.loan_payment_history)
		if total_paid > self.loan_amount:
			frappe.throw(f"Total Payments ({total_paid}) can not exceed loan amount"({self.loan_amount}))

	def update_loan_payment(self,paid_amount,payment_date):
		"""Record a payment in Loan Payment History when Salary Slip deducts the loan component."""

		if self.remaining_amount is None:
			self.remaining_amount = self.loan_amount  # Initialize remaining amount if not set

		

		# manual_paid = self.loan_paid
		# Calculate remaing amount
		# total_paid = self.get_total_paid_loan() + paid_amount + manual_paid
		# remaining_amount = max (0,self.loan_amount - total_paid)
		remaining_amount = max(0, self.remaining_amount - paid_amount)
		
		# Append a new entry to Loan Payment History
		self.append("loan_payment_history", {
			"loan_id": self.name,
			"payment_date": payment_date,
			"paid_amount": paid_amount,
			"remaining_amount": remaining_amount
		})
		

		#Update loan status if fully paid
		if remaining_amount == 0 :
			self.status = "Completed"
		self.save()

	def get_total_paid_loan(self):
		"""Calculate the total amount paid for this loan."""
		return sum(entry.paid_amount for entry in self.loan_payment_history)
	
	def get_total_manual_paid(self):
		"""Calculate the total manually paid amount from the Manual Loan Payment history table."""
		return sum(entry.paid_amount for entry in self.manual_paid_history)

	
	def update_remaining_amount(self):

		"""Update the remaining loan balance after payments are made."""
		# Get total paid amount from payment history
		if self.remaining_amount is None:
			self.remaining_amount = self.loan_amount

		current_remaining_amount = self.remaining_amount or self.loan_amount  # **Use updated remaining amount**
		total_paid = self.get_total_paid_loan() + self.get_total_manual_paid() + self.loan_paid 
		
		# Calculate the remaining amount by subtracting the total paid from the loan amount
		remaining_amount = max(0,self.loan_amount - total_paid)


		# Log manual payment in Manual Loan Payment table
		if self.loan_paid:
			self.append("manual_paid_history", {
				"paid_date": today(),  # Store in YYYY-MM-DD format
				"paid_amount": self.loan_paid,
				"remaining_amount":remaining_amount
			})
			self.loan_paid = 0 

		# If the remaining amount has changed, update the field
		if self.remaining_amount != remaining_amount:
			self.remaining_amount = remaining_amount
			# Save the document without triggering recursion
			frappe.db.set_value("Loan Management", self.name, "remaining_amount", remaining_amount)
			frappe.db.commit() 
		if remaining_amount == 0 :
			self.status = "Completed"
			frappe.db.set_value("Loan Management", self.name, "status", "Completed")
			frappe.db.commit()
		

			
			
			

			
		

		
		

		
		

	
