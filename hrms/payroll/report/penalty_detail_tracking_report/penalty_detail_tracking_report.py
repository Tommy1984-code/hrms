# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_months, getdate

def execute(filters=None):
    columns = get_columns()
    data_rows = get_data(filters)
    return columns, data_rows

def get_columns():
    return [
        {"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Data", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Monthly Deduction", "fieldname": "monthly_deduction", "fieldtype": "Currency", "width": 120},
        {"label": "Remaining Amount", "fieldname": "remaining_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Total Penalty", "fieldname": "total_penalty", "fieldtype": "Currency", "width": 120},
        {"label": "Payment Details", "fieldname": "payment_details", "fieldtype": "Data", "width": 400},
        {"label": "Manual Payment Details", "fieldname": "manual_payment_details", "fieldtype": "Data", "width": 400},
    ]

def get_data(filters=None):
    employee = filters.get("employee")
    company = filters.get("company")

    params = {"employee": employee}
    if company:
        params["company"] = company

    # Fetch penalty records
    penalties = frappe.db.sql("""
        SELECT pm.name AS penalty_id, pm.employee AS employee_id, e.employee_name, e.company,
               pm.total_penalty, pm.monthly_deduction, pm.start_date, pm.end_date, pm.remaining_amount
        FROM `tabPenalty Management` pm
        LEFT JOIN `tabEmployee` e ON e.name = pm.employee
        WHERE pm.employee = %(employee)s
        {company_clause}
        AND pm.is_active = 1
    """.format(
        company_clause="AND e.company = %(company)s" if company else ""
    ), params, as_dict=True)

    results = []
    for p in penalties:
        row = {
            "employee_id": p["employee_id"],
            "employee_name": p["employee_name"],
            "monthly_deduction": p["monthly_deduction"],
            "remaining_amount": p["remaining_amount"],
            "total_penalty": p["total_penalty"],
        }

        # ================= Penalty Payment History =================
        penalty_history = frappe.db.sql("""
            SELECT payment_date, paid_amount, remaining_amount
            FROM `tabPenalty Payment History`
            WHERE parent = %s
            ORDER BY payment_date
        """, p["penalty_id"], as_dict=True)

        payment_details = []
        total_paid = 0
        for idx, ph in enumerate(penalty_history, start=1):
            payment_details.append({
                "no": idx,
                "month": ph["payment_date"].strftime("%Y-%m-%d"),
                "deduction": ph["paid_amount"],
                "remaining": ph["remaining_amount"]
            })
            total_paid += ph["paid_amount"]
        row["payment_details"] = payment_details

        # ================= Manual Paid Penalty History =================
        manual_history = frappe.db.sql("""
            SELECT paid_date, paid_amount, remaining_amount
            FROM `tabManual Penalty Payment History`
            WHERE parent = %s
            ORDER BY paid_date
        """, p["penalty_id"], as_dict=True)

        manual_details = []
        manual_total = 0
        for idx, mh in enumerate(manual_history, start=1):
            manual_details.append({
                "no": idx,
                "month": mh["paid_date"].strftime("%Y-%m-%d"),
                "deduction": mh["paid_amount"],
                "remaining": mh["remaining_amount"]
            })
            manual_total += mh["paid_amount"]
        row["manual_payment_details"] = manual_details

        # Total paid including manual
        row["penalty_paid"] = total_paid + manual_total
        row["remaining_amount"] = (p["total_penalty"] or 0) - row["penalty_paid"]

        results.append(row)

    return results

def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months

