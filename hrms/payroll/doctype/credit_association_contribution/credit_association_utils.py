import frappe
from frappe.utils import flt
from hrms.payroll.utils import has_base_changed

def update_employee_credit_association(doc, method=None):
    """
    Triggered whenever an Employee is updated.
    Adjusts monthly deduction for active (Ongoing) and paused (Paused) contributions.
    """
    # Only proceed if 'base' field changed
    if not has_base_changed(doc, ["base"]):
        return
    if not doc.base:
        return

    employee = doc.name
    base_salary = flt(doc.base)

    contributions = frappe.get_all(
        "Credit Association Contribution",
        filters={
            "employee": employee,
            "status": ["in", ["Ongoing", "Paused"]]
        },
        fields=["name", "deduction_percent"]
    )

    for c in contributions:
        contrib_doc = frappe.get_doc("Credit Association Contribution", c.name)
        contrib_doc.base_salary = base_salary
        contrib_doc.update_deduction_percent()
        contrib_doc.save(ignore_permissions=True)

    if contributions:
        frappe.msgprint(
            f"Updated monthly deduction for {len(contributions)} credit association record(s) for Employee <b>{employee}</b> due to base salary change."
        )
