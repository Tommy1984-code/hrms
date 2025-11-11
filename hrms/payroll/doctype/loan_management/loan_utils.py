import frappe
from frappe.utils import flt
from hrms.payroll.utils import has_base_changed

def update_employee_loans(doc, method=None):
    """
    Triggered whenever an Employee is updated.
    Updates the base salary and recalculates monthly repayment for active (Ongoing or Paused) loans.
    Does NOT change remaining_amount.
    """
    # Only proceed if 'base' field changed
    if not has_base_changed(doc, ["base"]):
        return
    if not doc.base:
        return

    employee = doc.name
    base_salary = flt(doc.base)

    # Fetch active (Ongoing) and paused (Paused) loans
    loans = frappe.get_all(
        "Loan Management",
        filters={
            "employee": employee,
            "status": ["in", ["Ongoing", "Paused"]]
        },
        fields=["name", "monthly_deduction", "loan_amount", "deduction_percent", "remaining_amount"]
    )

    for l in loans:
        loan_doc = frappe.get_doc("Loan Management", l.name)

        # Update base salary
        loan_doc.base_salary = base_salary

        # If this loan uses a percentage deduction model
        if loan_doc.deduction_percent:
            new_repayment = flt(base_salary) * (flt(loan_doc.deduction_percent) / 100)

            # Repayment should not exceed remaining balance
            if loan_doc.remaining_amount is not None:
                new_repayment = min(new_repayment, flt(loan_doc.remaining_amount))

            loan_doc.monthly_repayment_amount = new_repayment

            # Update Loan salary component in deductions table
            component_name = "Loan Repayment"
            component = frappe.get_value("Salary Component", {"name": component_name}, ["name", "salary_component_abbr"])
            if component:
                existing_entry = None
                for d in loan_doc.get("deductions") or []:
                    if d.salary_component == component_name:
                        existing_entry = d
                        break

                if existing_entry:
                    existing_entry.amount = new_repayment
                else:
                    loan_doc.append("deductions", {
                        "salary_component": component[0],
                        "abbr": component[1],
                        "amount": new_repayment
                    })

            loan_doc.save(ignore_permissions=True)

    if loans:
        frappe.msgprint(
            f"Updated monthly repayment for {len(loans)} loan record(s) for Employee <b>{employee}</b> due to base salary change."
        )
