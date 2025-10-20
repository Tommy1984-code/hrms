# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, getdate


class CreditAssociationContribution(Document):

    def before_save(self):
        if not self.employee:
            return

        # --- Fetch Employee Base ---
        base_salary = frappe.db.get_value("Employee", self.employee, "base")
        if not base_salary:
            frappe.msgprint(f"Employee {self.employee} does not have a base salary set.")
            return
        self.base_salary = flt(base_salary)

        # --- Recalculate monthly deduction based on percent ---
        self.update_deduction_percent()

    def validate(self):
        # Deduction percent minimum 5%
        if self.deduction_percent and flt(self.deduction_percent) < 5:
            frappe.throw("Deduction percent cannot be less than 5%.")

    # -----------------------------
    # Calculate Monthly Deduction
    # -----------------------------
    def update_deduction_percent(self):
        if not self.deduction_percent or not self.base_salary:
            return

        base = flt(self.base_salary)
        income_tax = self.calculate_tax(base)
        pension = base * 0.07
        taxable_amount = base - income_tax - pension

        self.monthly_deduction = flt(taxable_amount * (flt(self.deduction_percent) / 100), 2)

        # Update Salary Component in deductions table
        component_name = "Credit Association"
        component = frappe.get_value(
            "Salary Component", {"name": component_name}, ["name", "salary_component_abbr"]
        )
        if component:
            existing_entry = next(
                (d for d in (self.get("deductions") or []) if d.salary_component == component[0]), None
            )
            if existing_entry:
                existing_entry.amount = self.monthly_deduction
            else:
                self.append("deductions", {
                    "salary_component": component[0],
                    "abbr": component[1],
                    "amount": self.monthly_deduction
                })

    # -----------------------------
    # Income Tax Calculation
    # -----------------------------
    def calculate_tax(self, income):
        """Ethiopian tax system based on base salary"""
        if income >= 0 and income <= 2000:
            tax = 0
        elif income > 2000 and income <= 4000:
            tax = income * 0.15 - 300
        elif income > 4000 and income <= 7000:
            tax = income * 0.20 - 500
        elif income > 7000 and income <= 10000:
            tax = income * 0.25 - 850
        elif income > 10000 and income <= 14000:
            tax = income * 0.30 - 1350
        else:
            tax = income * 0.35 - 2050
        return tax

    # -----------------------------
    # Salary Slip Payment Recording
    # -----------------------------
    def update_credit_payment(self, paid_amount, payment_date):
        """Called from Salary Slip on_submit"""
        self.append("credit_association_payment_history", {
            "credit_assocation_id": self.name,
            "payment_date": payment_date,  # use salary slip month
            "paid_amount": paid_amount
        })

        # Update deductions table amount
        component_name = "Credit Association"
        component = frappe.get_value(
            "Salary Component", {"name": component_name}, ["name", "salary_component_abbr"]
        )
        if component:
            existing_entry = next(
                (d for d in (self.get("deductions") or []) if d.salary_component == component[0]), None
            )
            if existing_entry:
                existing_entry.amount = self.monthly_deduction

        self.save(ignore_permissions=True)
