import frappe
from frappe.utils import flt

def update_employee_penalties(doc, method=None):
    """
    Triggered whenever an Employee is updated.
    Adjusts only monthly deduction for active (Ongoing) and paused (Paused) penalties.
    Does NOT update remaining_amount.
    """
    if not doc.base:
        return

    employee = doc.name
    base_salary = flt(doc.base)

    # Fetch active (Ongoing) and paused (Paused) penalties
    penalties = frappe.get_all(
        "Penalty Management",
        filters={
            "employee": employee,
            "status": ["in", ["Ongoing", "Paused"]]
        },
        fields=["name", "monthly_deduction", "total_penalty", "deduction_percent", "remaining_amount"]
    )

    for p in penalties:
        penalty_doc = frappe.get_doc("Penalty Management", p.name)

        # Update base salary reference
        penalty_doc.base_salary = base_salary

        # Recalculate monthly deduction = base × deduction_percent / 100
        if penalty_doc.deduction_percent:
            new_deduction = flt(base_salary) * (flt(penalty_doc.deduction_percent) / 100)

            # Monthly deduction should never exceed remaining_amount
            if penalty_doc.remaining_amount is not None:
                new_deduction = min(new_deduction, flt(penalty_doc.remaining_amount))

            penalty_doc.monthly_deduction = new_deduction

            # Update Penalty salary component in deductions table
            component_name = "Penalty"
            component = frappe.get_value("Salary Component", {"name": component_name}, ["name", "salary_component_abbr"])
            if component:
                # Update existing entry if present
                existing_entry = None
                for d in penalty_doc.get("deductions") or []:
                    if d.salary_component == component_name:
                        existing_entry = d
                        break

                if existing_entry:
                    existing_entry.amount = new_deduction
                else:
                    penalty_doc.append("deductions", {
                        "salary_component": component[0],
                        "abbr": component[1],
                        "amount": new_deduction
                    })

            penalty_doc.save(ignore_permissions=True)

    if penalties:
        frappe.msgprint(
            f"Updated monthly deduction for {len(penalties)} penalty record(s) for Employee <b>{employee}</b> due to base salary change."
        )
