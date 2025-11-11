# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, getdate

class LoanManagement(Document):

    # -----------------------------
    # Before Save
    # -----------------------------
    def before_save(self):
        """Handle base salary, deductions, and manual payments before saving."""
        if not self.employee:
            return
        
        #--- Prevent duplicate loans for same employee & loan type ---
        existing = frappe.db.exists({
            "doctype": "Loan Management",
            "employee": self.employee,
            "loan_type": self.loan_type,
            "name": ("!=", self.name),  # exclude self if updating
            "status": ["in", ["Ongoing", "Paused"]]  # only active loans
        })
        if existing:
            frappe.throw(f"Employee {self.employee} already has an active loan of type '{self.loan_type}'.")


        # --- Fetch Employee Base ---
        base_salary = frappe.db.get_value("Employee", self.employee, "base")
        if not base_salary:
            frappe.msgprint(f"Employee {self.employee} does not have a base salary set.")
            return

        self.base_salary = flt(base_salary)

        # --- Deduction Calculation ---
        self.calculate_monthly_deduction()

        # --- Ensure Remaining Amount Set ---
        if self.remaining_amount is None:
            self.remaining_amount = flt(self.loan_amount or 0)

        # --- Cap deduction to remaining ---
        self.monthly_deduction = min(flt(self.monthly_deduction or 0), flt(self.remaining_amount or 0))

        # --- Add deduction to Salary Component ---
        self.add_loan_salary_component()

        # --- Manual Payment Handling ---
        if self.loan_paid:
            self._process_manual_loan_payment()
            self.loan_paid = 0

    # -----------------------------
    # Deduction Calculation
    # -----------------------------
    def calculate_monthly_deduction(self):
        """Calculate monthly deduction amount based on type."""
        if self.deduction_type == "Percentile" and self.deduction_percent:
            # Cost Sharing rule (≥10%)
            if self.loan_type == "Cost Sharing" and flt(self.deduction_percent) < 10:
                frappe.throw("Cost Sharing deduction percent cannot be less than 10%.")
            # Calculate percent-based deduction
            self.monthly_deduction = flt(self.base_salary) * (flt(self.deduction_percent) / 100)

        elif self.deduction_type == "Flat" and self.monthly_deduction:
            self.monthly_deduction = flt(self.monthly_deduction)
        else:
            self.monthly_deduction = 0

    # -----------------------------
    # Validation
    # -----------------------------
    def validate(self):
        """Run validation checks before saving."""
        if not self.employee:
            frappe.throw("Please select an Employee before saving.")

        if not self.loan_amount or self.loan_amount <= 0:
            frappe.throw("Loan amount must be greater than zero.")

        # Ensure Percentile & Cost Sharing rules
        if self.deduction_type == "Percentile":
            if not self.deduction_percent:
                frappe.throw("Please enter Deduction % Per Month for Percentile type.")
            if flt(self.deduction_percent) > 50:
                frappe.throw("Loan deduction percent cannot exceed 50% of base salary.")
            if self.loan_type == "Cost Sharing" and flt(self.deduction_percent) < 10:
                frappe.throw("Cost Sharing deduction percent cannot be less than 10%.")

        # Monthly deduction cannot exceed total loan
        if flt(self.monthly_deduction) > flt(self.loan_amount):
            frappe.throw("Monthly deduction cannot exceed total loan amount.")

        # Paid amount validation
        if self.loan_paid and flt(self.loan_paid) > flt(self.remaining_amount or 0):
            frappe.throw("Loan paid amount cannot exceed remaining balance.")

    # -----------------------------
    # Salary Component Integration
    # -----------------------------
    def add_loan_salary_component(self):
        """Ensure the loan deduction component is added or updated in deductions child table."""
        component_name = self.loan_type
        component = frappe.get_value(
            "Salary Component",
            {"name": component_name},
            ["name", "salary_component_abbr"]
        )

        if not component:
            frappe.msgprint(f"Salary Component '{component_name}' not found.")
            return

        adjusted_deduction = flt(self.monthly_deduction or 0)
        if self.remaining_amount is not None:
            adjusted_deduction = min(adjusted_deduction, flt(self.remaining_amount))

        # Update existing deduction entry if exists
        existing_entry = next(
            (entry for entry in (self.get("deductions") or [])
             if entry.salary_component == component[0]),
            None
        )

        if existing_entry:
            existing_entry.amount = adjusted_deduction
        else:
            self.append("deductions", {
                "salary_component": component[0],
                "abbr": component[1],
                "amount": adjusted_deduction
            })

    # -----------------------------
    # Manual Loan Payment
    # -----------------------------
    def _process_manual_loan_payment(self):
        """Record manual loan payments and adjust remaining balance."""
        paid_amount = flt(self.loan_paid)
        if paid_amount <= 0:
            return

        remaining = flt(self.remaining_amount or self.loan_amount or 0)
        new_remaining = max(0, remaining - paid_amount)

        self.append("manual_paid_history", {
            "paid_date": today(),
            "paid_amount": paid_amount,
            "remaining_amount": new_remaining
        })

        self.remaining_amount = new_remaining

        # Adjust monthly deduction if remaining < monthly_deduction
        if self.remaining_amount < flt(self.monthly_deduction):
            self.monthly_deduction = flt(self.remaining_amount)
            self.add_loan_salary_component()

        # Auto-complete loan
        if flt(self.remaining_amount) == 0:
            self.status = "Completed"

    # -----------------------------
    # Salary Slip Payment Recording
    # -----------------------------
    def update_loan_payment(self, paid_amount, payment_date):
        """Called from Salary Slip on_submit to record system payments."""
        remaining = max(0, flt(self.remaining_amount or 0) - flt(paid_amount))

        self.append("loan_payment_history", {
            "loan_id": self.name,
            "payment_date": payment_date,
            "paid_amount": paid_amount,
            "remaining_amount": remaining
        })

        self.remaining_amount = remaining

        # Adjust monthly deduction if remaining < monthly_deduction
        if self.remaining_amount < flt(self.monthly_deduction):
            self.monthly_deduction = flt(self.remaining_amount)
            self.add_loan_salary_component()

        # Mark complete if fully paid
        if flt(self.remaining_amount) == 0:
            self.status = "Completed"

        self.save(ignore_permissions=True)

			
			
			

			
		

		
		

		
		

	
