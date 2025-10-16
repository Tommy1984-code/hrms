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

        base_salary = frappe.db.get_value("Employee", self.employee, "base")
        if not base_salary:
            frappe.msgprint(f"Employee {self.employee} does not have a base salary set.")
            return

        self.base_salary = flt(base_salary)

        if self.deduction_percent:
            self.monthly_deduction = flt(self.base_salary) * (flt(self.deduction_percent) / 100)
            if self.remaining_amount is not None:
                self.monthly_deduction = min(self.monthly_deduction, flt(self.remaining_amount))
            else:
                self.remaining_amount = flt(self.total_penalty) if self.total_penalty else 0
                self.monthly_deduction = min(self.monthly_deduction, flt(self.remaining_amount))

        # ✅ Only add deduction to Salary Slip draft, do NOT record payment history
        self.add_penalty_salary_component()

        # Manual penalty payment (works as before)
        if self.penalty_paid:
            self._process_manual_penalty_payment()

        self.penalty_paid = 0
        self.manage_penalty_queue()

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
        """
        Adds Penalty component to Salary Slip deductions.
        ⚠️ Does NOT record payment history — history is only recorded on Salary Slip submit.
        """
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
        if paid_amount <= 0 or not self.is_active:
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
            self.set_next_penalty_ready()

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
    # Mark Next Penalty Ready
    # -----------------------------
    def set_next_penalty_ready(self):
        next_penalty = frappe.get_all(
            "Penalty Management",
            filters={
                "employee": self.employee,
                "is_active": 0,
                "status": "Paused"
            },
            order_by="queue_no ASC",
            fields=["name"],
            limit=1
        )
        if next_penalty:
            frappe.db.set_value("Penalty Management", next_penalty[0].name, "next_deduction_ready", 1)

    # -----------------------------
    # Activate Ready Penalty for Current Month
    # -----------------------------
    @staticmethod
    def activate_ready_penalty_for_month(employee):
        ready_penalties = frappe.get_all(
            "Penalty Management",
            filters={
                "employee": employee,
                "is_active": 0,
                "status": "Paused",
                "next_deduction_ready": 1
            },
            order_by="queue_no ASC",
            fields=["name"]
        )
        for p in ready_penalties:
            doc = frappe.get_doc("Penalty Management", p.name)
            doc.is_active = 1
            doc.status = "Ongoing"
            doc.next_deduction_ready = 0
            doc.save(ignore_permissions=True)
            frappe.msgprint(f"Penalty {doc.name} is now active for this month.")
            

    # -----------------------------
    # Salary Slip Payment Recording
    # -----------------------------
    def update_penalty_payment(self, paid_amount, payment_date,salary_month_start=None):
        """
        ✅ Called only from Salary Slip on_submit
        Records the penalty payment history.
        """
        if not self.is_active:
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
            self.set_next_penalty_ready()

        self.save()


# ===========================================================
# 🔹 HOOK WRAPPER FUNCTION (for Salary Slip before_insert)
# ===========================================================
def activate_ready_penalty_for_month(doc, method=None):
    """Wrapper for Frappe hook - activates next penalty before Salary Slip creation"""
    from hrms.payroll.doctype.penalty_management.penalty_management import PenaltyManagement

    if not getattr(doc, "employee", None):
        return

    PenaltyManagement.activate_ready_penalty_for_month(doc.employee)

