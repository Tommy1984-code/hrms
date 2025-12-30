# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_months

def execute(filters=None):
    columns = get_columns()
    data_rows = get_data(filters)
    return columns, data_rows

def get_columns():
    return [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 120},
        {"label": "Total Penalty", "fieldname": "total_penalty", "fieldtype": "Currency", "width": 120},
        {"label": "Monthly Deduction", "fieldname": "monthly_deduction", "fieldtype": "Currency", "width": 120},
        {"label": "Penalty Paid (Manual + Deduction)", "fieldname": "penalty_paid", "fieldtype": "Currency", "width": 140},
        {"label": "Remaining Amount", "fieldname": "remaining_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date", "width": 100},
        {"label": "End Date", "fieldname": "end_date", "fieldtype": "Date", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters=None):
    employee = filters.get("employee")
    company = filters.get("company")

    params = {"employee": employee}
    if company:
        params["company"] = company

    # Fetch penalty management records
    penalties = frappe.db.sql("""
        SELECT pm.name, pm.employee, e.employee_name, e.company, pm.total_penalty,
               pm.monthly_deduction, pm.start_date, pm.end_date, pm.remaining_amount,
               pm.status
        FROM `tabPenalty Management` pm
        LEFT JOIN `tabEmployee` e ON e.name = pm.employee
        WHERE pm.employee = %(employee)s
        {company_clause}
        AND pm.is_active = 1
    """.format(
        company_clause="AND e.company = %(company)s" if company else ""
    ), params, as_dict=True)

    for p in penalties:
        # Fetch sum of manual paid penalty history for this penalty
        manual_paid_sum = frappe.db.sql("""
            SELECT SUM(mp.paid_amount) 
            FROM `tabManual Penalty Payment History` mp
            WHERE mp.parent = %s
        """, p.name)[0][0] or 0

        # Sum of penalty_paid = manual + monthly deduction paid (if any)
        # Here you can customize to include already deducted monthly penalties if needed
        p["penalty_paid"] = manual_paid_sum

        # Optionally, calculate remaining amount after manual paid
        p["remaining_amount"] = (p["total_penalty"] or 0) - p["penalty_paid"]

    return penalties

# Optional helper if you want to generate months
def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months
