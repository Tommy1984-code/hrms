# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict


def execute(filters=None):
    columns = get_columns()
    data_rows = get_data(filters)

    # Fetch employee and loan details for the header
    employee_id = filters.get("employee")
    loan_type = filters.get("loan_type")

    employee_doc = frappe.get_doc("Employee", employee_id) if employee_id else None
    loan_doc = None

    

    if employee_id and loan_type:
        loan_doc = frappe.get_all("Loan Management",
                                  filters={"employee": employee_id, "loan_type": loan_type},
                                  fields=["name", "monthly_deduction","remaining_amount","loan_amount"],
                                  limit=1)
        loan_doc = loan_doc[0] if loan_doc else None

    summary_data = {
        "employee_id": employee_doc.name if employee_doc else "",
        "employee_name": employee_doc.employee_name if employee_doc else "",
        "monthly_deduction": loan_doc.monthly_deduction if loan_doc else 0,
        "remaining_amounts": loan_doc.remaining_amount if loan_doc else 0,
        "loan_amount": loan_doc.loan_amount if loan_doc else 0
    }

    # Attach summary info to each row (so it can be picked in the report)
    for row in data_rows:
        row.update(summary_data)

    return columns, data_rows


def get_columns():
    return [
        {"label": "Loan ID", "fieldname": "loan_id", "fieldtype": "Data", "width": 100},
        {"label": "Payment Date", "fieldname": "payment_date", "fieldtype": "Date", "width": 120},
        {"label": "Paid Amount", "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Remaining Amount", "fieldname": "remaining_amount", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters=None):
    # Fetch the employee, company, and loan_type from filters
    employee = filters.get("employee")
    company = filters.get("company")
    loan_type = filters.get("loan_type")

    # Prepare query parameters
    params = {
        "employee": employee,
        "company": company,
        "loan_type": loan_type,
    }

    # Construct the query to fetch the required data from Loan Payment History
    query = """
        SELECT 
            lph.name AS loan_id,
            lph.payment_date,
            lph.paid_amount,
            lph.remaining_amount
        FROM `tabLoan Payment History` lph
        LEFT JOIN `tabLoan Management` lm ON lm.name = lph.loan_id
        LEFT JOIN `tabEmployee` e ON lm.employee = e.name
        WHERE lm.employee = %(employee)s
        {company_clause}
        AND lm.loan_type = %(loan_type)s

        ORDER BY lph.payment_date DESC
    """.format(
        company_clause="AND e.company = %(company)s" if company else "",
        
    )

    # Fetch results from the database
    results = frappe.db.sql(query, params, as_dict=True)

    return results

def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date

    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)

    return months