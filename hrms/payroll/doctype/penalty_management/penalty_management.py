
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class PenaltyManagement(Document):

    # -----------------------------
    # Before Save
    # -----------------------------
    def before_save(self):
        if not self.employee:
            return

        # Fetch employee base salary
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

        # Add/update penalty salary component
        self.add_penalty_salary_component()

        # Handle manual payment entered in penalty_paid
        if self.penalty_paid:
            self._process_manual_penalty_payment()

        # Reset penalty_paid field to 0 after processing
        self.penalty_paid = 0

        # Manage penalty queue (paused/ongoing)
        self.manage_penalty_queue()

        # Activate next penalty if needed (for next month)
        self.activate_next_penalty_if_ready()

        # Update status if fully paid
        if flt(self.remaining_amount) == 0:
            self.status = "Completed"
            self.is_active = 0

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
        component_name = "Penalty"
        component = frappe.get_value("Salary Component", {"name": component_name}, ["name", "salary_component_abbr"])
        if not component:
            frappe.msgprint(f"Salary Component '{component_name}' not found.")
            return

        adjusted_deduction = flt(self.monthly_deduction)
        if self.remaining_amount is not None:
            adjusted_deduction = min(adjusted_deduction, flt(self.remaining_amount))

        existing_entry = next(
            (entry for entry in (self.get("deductions") or []) if entry.salary_component == component[0]), None
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
    # Manual Penalty Payment
    # -----------------------------
    def _process_manual_penalty_payment(self):
        paid_amount = flt(self.penalty_paid)
        if paid_amount <= 0:
            return

        remaining = flt(self.remaining_amount or self.total_penalty or 0)
        new_remaining = max(0, remaining - paid_amount)

        self.append("manual_paid_penalty_history", {
            "paid_date": today(),
            "paid_amount": paid_amount,
            "remaining_amount": new_remaining
        })

        self.remaining_amount = new_remaining

        if self.remaining_amount < flt(self.monthly_deduction):
            self.monthly_deduction = flt(self.remaining_amount)
            self.add_penalty_salary_component()

        if flt(self.remaining_amount) == 0:
            self.status = "Completed"
            self.is_active = 0
            # Do NOT activate next penalty immediately; it will be done next month

    # -----------------------------
    # Penalty Queue Management
    # -----------------------------
    def manage_penalty_queue(self):
        existing = frappe.get_all(
            "Penalty Management",
            filters={"employee": self.employee, "name": ["!=", self.name]},
            fields=["name", "is_active", "queue_no", "status"],
            order_by="queue_no ASC"
        )

        active = [p for p in existing if p.is_active]

        if self.status == "Completed":
            self.is_active = 0
            return

        if active:
            self.is_active = 0
            self.status = "Paused"
            max_queue = max([p.queue_no for p in existing if p.queue_no] or [0])
            self.queue_no = max_queue + 1
        else:
            self.is_active = 1
            self.status = "Ongoing"
            if not self.queue_no:
                self.queue_no = 1

    # -----------------------------
    # Activate Next Penalty (Next Month)
    # -----------------------------
    def activate_next_penalty_if_ready(self):
        """Activate next penalty only if no active penalty exists."""
        # Check if current penalty is completed
        if flt(self.remaining_amount) > 0:
            return

        # Only activate next if no other active penalties
        active = frappe.get_all(
            "Penalty Management",
            filters={"employee": self.employee, "is_active": 1, "status": "Ongoing"},
            fields=["name"]
        )
        if active:
            return

        # Find the next paused penalty in queue
        next_penalty = frappe.get_all(
            "Penalty Management",
            filters={
                "employee": self.employee,
                "is_active": 0,
                "status": "Paused"
            },
            fields=["name"],
            order_by="queue_no ASC",
            limit=1
        )
        if next_penalty:
            doc = frappe.get_doc("Penalty Management", next_penalty[0].name)
            doc.is_active = 1
            doc.status = "Ongoing"
            doc.save(ignore_permissions=True)
            frappe.msgprint(f"Next penalty {doc.name} is now active in the new cycle.")

    # -----------------------------
    # Salary Slip Payment Recording
    # -----------------------------
    def update_penalty_payment(self, paid_amount, payment_date):
        if self.is_active != 1:
            return

        if self.remaining_amount is None:
            self.remaining_amount = flt(self.total_penalty) or 0

        remaining = max(0, flt(self.remaining_amount) - flt(paid_amount))

        self.append("penalty_payment_history", {
            "penalty_id": self.name,
            "payment_date": payment_date,
            "paid_amount": paid_amount,
            "remaining_amount": remaining
        })

        self.remaining_amount = remaining

        if self.remaining_amount < flt(self.monthly_deduction):
            self.monthly_deduction = flt(self.remaining_amount)
            self.add_penalty_salary_component()

        if flt(self.remaining_amount) == 0:
            self.status = "Completed"
            self.is_active = 0

        self.save()
