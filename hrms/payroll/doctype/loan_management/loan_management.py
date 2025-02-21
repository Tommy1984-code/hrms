# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe


class LoanManagement(Document):
    
	def validate(self):
		self.check_duplicate_load_type()
		self.add_loan_salary_component()

	
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
		"""Fetch and add the 'loan' salary component to the Deductions child table."""
		loan_component = frappe.get_value("Salary Component", {"name": "Loan"}, ["name", "amount"])

		if loan_component:
			# Check if the component is already in the deductions table
			if not any(detail.salary_component == loan_component[0] for detail in self.deductions):
				# Create a new entry for the child table
				deduction_entry = {
					'salary_component': loan_component[0],  # Name of the component
					'amount': self.monthly_deduction , # Default amount
					
				}
				# Append to the child table
				self.append('deductions', deduction_entry)


	def validate_remaining_balance(self):
		"""Ensure the remaining loan balance is not negative."""
		total_paid = sum(entry.paid_amount for entry in self.loan_payment_history)
		if total_paid > self.loan_amount:
			frappe.throw(f"Total Payments ({total_paid}) can not exceed loan amount"({self.loan_amount}))

	def update_loan_payment(self,paid_amount,payment_date):
		"""Record a payment in Loan Payment History when Salary Slip deducts the loan component."""

		# Calculate remaing amount
		total_paid = self.get_total_paid_loan() + paid_amount
		remaining_amount = max (0,self.loan_amount - total_paid)
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




	
