# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import today
import frappe


class LoanManagement(Document):

    
	def validate(self):
		self.check_duplicate_load_type()
		self.validate_monthly_deduction()
		self.validate_loan_paid_amount()
		self.update_remaining_amount()
		# self.add_loan_salary_component()
		if self.loan_paid:
			self.loan_paid = 0

	def on_update(self):
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

			loan_name = frappe.get_value("Loan Management", {"employee": self.employee, "status": "Ongoing"},"name")

			frappe.msgprint(f"my employee is : {loan_name}")
			
			if loan_name:

				latest_remaining_amount = frappe.db.get_value("Loan Management", loan_name, "remaining_amount")
				latest_monthly_deduction = frappe.db.get_value("Loan Management", loan_name, "monthly_deduction")
				
				frappe.msgprint(f"remaing amount is : {latest_remaining_amount}")
				frappe.msgprint(f"montly deduction is : {latest_monthly_deduction}")


				if latest_remaining_amount > 0:

				# Adjust the deduction amount if the remaining amount is less than the usual deduction
					adjusted_deduction = min(latest_monthly_deduction, latest_remaining_amount)


					# Check if the loan component already exists in deductions
					existing_entry = next((detail for detail in self.deductions if detail.salary_component == loan_component[0]), None)
					
					if existing_entry:
						
						existing_entry.amount = adjusted_deduction
						frappe.db.set_value("Salary Detail", existing_entry.name, "amount", adjusted_deduction)  # 🔥 Update directly without recursion
						
					else:
						deduction_entry = {
							'salary_component': loan_component[0],  # Name of the component
							'amount': adjusted_deduction,
							
						}
						# Append to the child table
						self.append('deductions', deduction_entry)
					
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
		manual_paid = self.loan_paid
		# Calculate remaing amount
		total_paid = self.get_total_paid_loan() + paid_amount + manual_paid
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
	
	def update_remaining_amount(self):

		"""Update the remaining loan balance after payments are made."""
		# Get total paid amount from payment history
		current_remaining_amount = self.remaining_amount or self.loan_amount  # **Use updated remaining amount**
		total_paid = self.get_total_paid_loan() + self.loan_paid

		# Calculate the remaining amount by subtracting the total paid from the loan amount
		remaining_amount = max(0, current_remaining_amount - total_paid)

		# If this is the first time, set the initial remaining amount as the loan amount
		if not self.remaining_amount:
			self.remaining_amount = self.loan_amount

		# Log manual payment in Manual Loan Payment table
		if self.loan_paid:
			self.append("manual_paid_history", {
				"paid_date": today(),  # Store in YYYY-MM-DD format
				"paid_amount": self.loan_paid
			})

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
		

			
			
			

			
		

		
		

		
		

	
