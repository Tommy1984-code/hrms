
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

class PenaltyManagement(Document):

    def before_save(self):
        if not self.employee:
            return

        # Fetch employee base
        base_salary = frappe.db.get_value("Employee", self.employee, "base")
        if not base_salary:
            frappe.msgprint(f"Employee {self.employee} does not have a base salary set.")
            return

        self.base_salary = flt(base_salary)

        # Calculate monthly deduction = base × deduction_percent / 100
        if self.deduction_percent:
            self.monthly_deduction = flt(self.base_salary) * (flt(self.deduction_percent) / 100)

            # Ensure deduction never exceeds remaining_amount
            if self.remaining_amount is not None:
                self.monthly_deduction = min(self.monthly_deduction, flt(self.remaining_amount))
            else:
                self.remaining_amount = flt(self.total_penalty) if self.total_penalty else 0
                self.monthly_deduction = min(self.monthly_deduction, flt(self.remaining_amount))

        # Add/update Penalty salary component
        self.add_penalty_salary_component()

        # Handle manual payment entered in penalty_paid
        if self.penalty_paid:
            self._process_manual_penalty_payment()

        # Reset penalty_paid field to 0 after processing
        self.penalty_paid = 0

        # Manage penalty queue
        self.manage_penalty_queue()

        # Update status if fully paid
        if flt(self.remaining_amount) == 0:
            self.status = "Completed"

    # -----------------------------
    # Validation
    # -----------------------------
    def validate(self):
        if not self.employee:
            frappe.throw("Please select an Employee before saving.")

        if self.deduction_percent and flt(self.deduction_percent) > 33:
            frappe.throw("Deduction percent cannot exceed 33% of base salary.")

    # -----------------------------
    # Salary Component Integration
    # -----------------------------
    def add_penalty_salary_component(self):
        """Update or override 'Penalty' salary component in deductions child table."""
        component_name = "Penalty"
        component = frappe.get_value("Salary Component", {"name": component_name}, ["name", "salary_component_abbr"])
        if not component:
            frappe.msgprint(f"Salary Component '{component_name}' not found.")
            return

        adjusted_deduction = flt(self.monthly_deduction)

        # If remaining amount is less than monthly_deduction, adjust it
        if self.remaining_amount is not None:
            adjusted_deduction = min(adjusted_deduction, flt(self.remaining_amount))

        # Update existing Penalty entry if exists
        existing_entry = None
        for entry in self.get("deductions") or []:
            if entry.salary_component == component[0]:
                existing_entry = entry
                break

        if existing_entry:
            existing_entry.amount = adjusted_deduction
        else:
            self.append("deductions", {
                "salary_component": component[0],
                "abbr": component[1],
                "amount": adjusted_deduction
            })

        frappe.db.commit()

    # -----------------------------
    # Manual Penalty Payment
    # -----------------------------
    def _process_manual_penalty_payment(self):
        paid_amount = flt(self.penalty_paid)
        if paid_amount <= 0:
            return

        remaining = flt(self.remaining_amount or self.total_penalty or 0)
        new_remaining = max(0, remaining - paid_amount)

        # Append manual payment history
        self.append("manual_paid_penalty_history", {
            "paid_date": today(),
            "paid_amount": paid_amount,
            "remaining_amount": new_remaining
        })

        # Update remaining_amount
        self.remaining_amount = new_remaining

        # Recalculate monthly deduction if remaining_amount < current deduction
        if self.remaining_amount < flt(self.monthly_deduction):
            self.monthly_deduction = flt(self.remaining_amount)
            # Update salary component to match
            self.add_penalty_salary_component()

        # Update status if fully paid
        if flt(self.remaining_amount) == 0:
            self.status = "Completed"

    # -----------------------------
    # Penalty Queue Management
    # -----------------------------
    def manage_penalty_queue(self):
        existing = frappe.get_all("Penalty Management",
                                  filters={"employee": self.employee},
                                  fields=["name", "is_active", "queue_no", "status"],
                                  order_by="queue_no ASC")

        active = [p for p in existing if p.is_active]
        if active and self.is_active:
            # Keep queue_no unchanged
            self.is_active = 0
            self.status = "Paused"  # Paused for waiting
        else:
            self.is_active = 1
            self.status = "Ongoing"
            if not self.queue_no:
                max_queue = max([p.queue_no for p in existing] or [0])
                self.queue_no = max_queue + 1

    def on_update(self):
        if self.status == "Completed":
            next_penalty = frappe.get_all("Penalty Management",
                                          filters={
                                              "employee": self.employee,
                                              "is_active": 0,
                                              "status": ["in", ["Paused"]]
                                          },
                                          fields=["name"],
                                          order_by="queue_no ASC",
                                          limit=1)
            if next_penalty:
                doc = frappe.get_doc("Penalty Management", next_penalty[0].name)
                doc.is_active = 1
                doc.status = "Ongoing"
                doc.save(ignore_permissions=True)
                frappe.msgprint(f"Next penalty {doc.name} is now active.")

    # -----------------------------
    # Salary Slip Payment Recording
    # -----------------------------
    def update_penalty_payment(self, paid_amount, payment_date):
        """Record a salary slip deduction in penalty_payment_history"""
        if self.remaining_amount is None:
            self.remaining_amount = flt(self.total_penalty) or 0

        remaining = max(0, flt(self.remaining_amount) - flt(paid_amount))

        self.append("penalty_payment_history", {
            "payment_date": payment_date,
            "paid_amount": paid_amount,
            "remaining_amount": remaining
        })

        self.remaining_amount = remaining

        # Recalculate monthly deduction if remaining_amount < current deduction
        if self.remaining_amount < flt(self.monthly_deduction):
            self.monthly_deduction = flt(self.remaining_amount)
            self.add_penalty_salary_component()

        if flt(self.remaining_amount) == 0:
            self.status = "Completed"

        self.save()
