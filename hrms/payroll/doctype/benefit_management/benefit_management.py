# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import flt


class BenefitManagement(Document):

    # --------------------------------------------------
    # Before Save
    # --------------------------------------------------
    def before_save(self):
        """Prepare benefit details before saving."""
        if not self.employee:
            return

        # --- Sync Employee Base ---
        self.update_base_salary()

        # --- Skip if not ongoing ---
        if self.status in ["Paused", "Closed"]:
            self.earnings = []
            return

        # --- Calculate Monthly Earning ---
        self.calculate_monthly_earning()

        # --- Add Benefit Salary Component ---
        self.add_benefit_salary_component()

        # --- Update Total Paid from History ---
        self.update_total_paid()

    # --------------------------------------------------
    # Update Base Salary from Employee
    # --------------------------------------------------
    def update_base_salary(self):
        """Fetch latest base salary from Employee doctype."""
        base_salary = frappe.db.get_value("Employee", self.employee, "base")
        if not base_salary:
            frappe.msgprint(f"Employee {self.employee} does not have a base salary set.")
            return
        self.base_salary = flt(base_salary)

    # --------------------------------------------------
    # Calculate Monthly Earning
    # --------------------------------------------------
    def calculate_monthly_earning(self):
        """Determine monthly earning based on Flat or Percentile."""
        if self.earning_type == "Percentile" and self.earning_percent:
            self.monthly_earning = flt(self.base_salary) * (flt(self.earning_percent) / 100)
        elif self.earning_type == "Flat":
            self.monthly_earning = flt(self.monthly_earning or 0)
        else:
            self.monthly_earning = 0

    # --------------------------------------------------
    # Add Benefit to Earnings Table
    # --------------------------------------------------
    def add_benefit_salary_component(self):
        """Ensure benefit component is added or updated in earnings child table."""
        component_name = self.benefit_type
        component = frappe.get_value(
            "Salary Component",
            {"name": component_name, "benefit_component": 1},
            ["name", "salary_component_abbr"]
        )

        if not component:
            frappe.msgprint(f"Salary Component '{component_name}' not found or not marked as Benefit Component.")
            return

        # Update existing earning entry if exists
        existing_entry = next(
            (entry for entry in (self.get("earnings") or [])
             if entry.salary_component == component[0]),
            None
        )

        if existing_entry:
            existing_entry.amount = flt(self.monthly_earning)
        else:
            self.append("earnings", {
                "salary_component": component[0],
                "abbr": component[1],
                "amount": flt(self.monthly_earning)
            })

    # --------------------------------------------------
    # Total Paid Tracker
    # --------------------------------------------------
    def update_total_paid(self):
        """Sum total paid from the Benefit Payment History table."""
        total = 0
        for entry in (self.get("benefit_payment_history") or []):
            total += flt(entry.get("paid_amount", 0))
        self.total_paid = total

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------
    def validate(self):
        """Ensure valid benefit setup."""
        if not self.employee:
            frappe.throw("Please select an Employee before saving.")
        if not self.benefit_type:
            frappe.throw("Please select a Benefit Type.")
        if self.earning_type == "Percentile" and not self.earning_percent:
            frappe.throw("Please enter Earning % for Percentile type.")

    # --------------------------------------------------
    # Hook for Salary Slip (called monthly)
    # --------------------------------------------------
    def fetch_for_salary_slip(self, salary_slip_start, salary_slip_end):
        """
        Called from Salary Slip to fetch benefit details if Ongoing.
        Handles prorated amount only in Salary Slip, not here.
        """
        if self.status != "Ongoing":
            return None

        # Skip if completely outside this month range
        if self.end_date and self.end_date < salary_slip_start:
            return None
        if self.start_date and self.start_date > salary_slip_end:
            return None

        return {
            "salary_component": self.benefit_type,
            "amount": flt(self.monthly_earning)
        }
