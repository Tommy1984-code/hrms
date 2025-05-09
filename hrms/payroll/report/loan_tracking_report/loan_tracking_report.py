# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
        {"label": "Loan ID", "fieldname": "loan_id", "fieldtype": "Data", "width": 60},
        {"label": "Payment Date", "fieldname": "payment_date", "fieldtype": "Date", "width": 120},
        {"label": "Paid Amount", "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Remaining Amount", "fieldname": "remaining_amount", "fieldtype": "Currency", "width": 120},
    ]

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

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

    if not employee:
        frappe.throw("Please select an Employee.")  # Make sure employee filter is selected

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
        {loan_type_clause}
        ORDER BY lph.payment_date DESC
    """.format(
        company_clause="AND e.company = %(company)s" if company else "",
        loan_type_clause="AND lm.loan_type = %(loan_type)s" if loan_type else ""
    )

    # Fetch results from the database
    results = frappe.db.sql(query, params, as_dict=True)

    # If no results, return empty data (to prevent errors)
    if not results:
        return []

    return results

def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date

    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)

    return months