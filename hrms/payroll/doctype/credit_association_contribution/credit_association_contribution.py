# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, getdate


import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate

class CreditAssociationContribution(Document):

    def before_save(self):
        if not self.employee:
            return
        
        # --- Prevent duplication for the same employee ---
        existing = frappe.db.exists({
            "doctype": "Credit Association Contribution",
            "employee": self.employee,
            "name": ("!=", self.name)  # exclude self if updating
        })
        if existing:
            frappe.throw(f"A Credit Association Contribution already exists for Employee {self.employee}.")

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
            "Salary Component",
            {"name": component_name},
            ["name", "salary_component_abbr"]
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
        if income <= 2000:
            tax = 0
        elif income <= 4000:
            tax = income * 0.15 - 300
        elif income <= 7000:
            tax = income * 0.20 - 500
        elif income <= 10000:
            tax = income * 0.25 - 850
        elif income <= 14000:
            tax = income * 0.30 - 1350
        else:
            tax = income * 0.35 - 2050
        return tax

    # -----------------------------
    # Salary Slip Payment Recording
    # -----------------------------
    def update_credit_payment(self, paid_amount, payment_date):
        """Called from Salary Slip on_submit — records payment and updates total paid amount"""

        # Normalize input
        paid_amount = flt(paid_amount)
        payment_date = getdate(payment_date)

        # Append payment to child table
        self.append("credit_association_payment_history", {
            "credit_assocation_id": self.name,
            "payment_date": payment_date,
            "paid_amount": paid_amount
        })
        self.save(ignore_permissions=True)

        # Recalculate total paid_amount from DB
        total_paid = frappe.db.sql(
            """
            SELECT COALESCE(SUM(paid_amount), 0)
            FROM `tabCredit Association Contribution Payment History`
            WHERE parent = %s
            """,
            (self.name,)
        )[0][0]

        # Update parent field in DB
        frappe.db.set_value(
            "Credit Association Contribution",
            self.name,
            "paid_amount",
            flt(total_paid),
            update_modified=True
        )
        frappe.db.commit()

        # Update in-memory value
        self.paid_amount = flt(total_paid)
   
	

