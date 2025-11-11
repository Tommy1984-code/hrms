import frappe
from frappe.utils import flt
from hrms.payroll.utils import has_base_changed

def update_employee_benefits(doc, method=None):
    """
    Triggered whenever an Employee is updated.
    Updates the base salary and recalculates benefit amount
    for active (Ongoing or Paused) Benefit Management records.
    """
    # Only proceed if 'base' field changed
    if not has_base_changed(doc, ["base"]):
        return
    if not doc.base:
        return

    employee = doc.name
    base_salary = flt(doc.base)

    # Fetch active (Ongoing or Paused) benefits
    benefits = frappe.get_all(
        "Benefit Management",
        filters={
            "employee": employee,
            "status": ["in", ["Ongoing", "Paused"]]
        },
        fields=["name", "earning_percent", "monthly_earning"]
    )

    for b in benefits:
        benefit_doc = frappe.get_doc("Benefit Management", b.name)

        # Update base salary
        benefit_doc.base_salary = base_salary

        # If this benefit uses a percentage model, recalc benefit_amount
        if benefit_doc.earning_percent:
            new_amount = flt(base_salary) * (flt(benefit_doc.earning_percent) / 100)
            benefit_doc.monthly_earning = new_amount

        # Save quietly
        benefit_doc.save(ignore_permissions=True)

    if benefits:
        frappe.msgprint(
            f"Updated benefit amount for {len(benefits)} record(s) of Employee <b>{employee}</b> due to base salary change."
        )
