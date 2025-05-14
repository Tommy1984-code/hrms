# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
    return [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": "Basic Pay", "fieldname": "basic", "fieldtype": "Currency", "width": 100},
        {"label": "Hardship Allowance", "fieldname": "hardship", "fieldtype": "Currency", "width": 120},
        {"label": "Commission", "fieldname": "commission", "fieldtype": "Currency", "width": 100},
        {"label": "Overtime", "fieldname": "overtime", "fieldtype": "Currency", "width": 100},
        {"label": "Duty", "fieldname": "duty", "fieldtype": "Currency", "width": 100},
        {"label": "Gross Pay", "fieldname": "gross", "fieldtype": "Currency", "width": 100},
        {"label": "Company Pension", "fieldname": "company_pension", "fieldtype": "Currency", "width": 120},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency", "width": 100},
        {"label": "Employee Pension", "fieldname": "employee_pension", "fieldtype": "Currency", "width": 100},
        {"label": "Salary Advance", "fieldname": "salary_advance", "fieldtype": "Currency", "width": 120},
        {"label": "Loan", "fieldname": "loan", "fieldtype": "Currency", "width": 120},
        {"label": "Gym", "fieldname": "gym", "fieldtype": "Currency", "width": 100},
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 100},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 100},
    ]


def get_data(filters):
    

    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    employee = filters.get("employee")
    company = filters.get("company")
    payment_type = filters.get("payment_type")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    data = []
    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)
        month_label = month.strftime('%B %Y')

        query = """
            SELECT ss.name AS salary_slip, ss.employee, ss.gross_pay, ss.net_pay,
                   ss.total_deduction, ss.payment_type,
                   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
              {employee_clause}
              {company_clause}
              {payment_type_clause}
            ORDER BY ss.end_date DESC
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
			payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "employee" : employee,
            "company" : company
        }

        if payment_type:
            params["payment_type"] = payment_type

        results = frappe.db.sql(query, params, as_dict=True)

        # Get latest salary slip per employee for the month
        latest_slips = {}
        for row in results:
            emp = row.employee
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
            if emp not in latest_slips or current_index > payment_order.index(latest_slips[emp].payment_type):
                latest_slips[emp] = row

        for emp in latest_slips:
            slip = latest_slips[emp]["salary_slip"]
            slip_data = [row for row in results if row.salary_slip == slip]

            row_dict = {
                "month": month_label,
                "basic": 0,
                "hardship": 0,
                "commission": 0,
                "overtime": 0,
                "duty": 0,
                "gross": 0,
                "company_pension": 0,
                "income_tax": 0,
                "employee_pension": 0,
                "salary_advance": 0,
                "loan": 0,
                "gym": 0,
                "total_deduction": 0,
                "net_pay": 0,
            }

            for r in slip_data:
                amt = r.amount or 0
                comp = r.abbr or r.salary_component

                if r.parentfield == "earnings":
                    if comp in ('B', 'VB'):
                        row_dict["basic"] += amt
                    elif comp == 'HDA':
                        row_dict["hardship"] += amt
                    elif comp == 'C':
                        row_dict["commission"] += amt
                    elif comp == 'OT':
                        row_dict["overtime"] += amt
                    elif comp == 'DY':
                        row_dict["duty"] += amt
                    
                elif r.parentfield == "deductions":
                    if comp == 'IT':
                        row_dict["income_tax"] += amt
                    elif comp == 'PS':
                        row_dict["employee_pension"] += amt
                    elif comp == 'APNI':
                        row_dict["salary_advance"] += amt
                    elif comp in ('HL', 'csl'):  # Loan types: Healthy Loan, Coast Sharing Loan
                        row_dict["loan"] += amt
                    elif comp == 'GM':
                        row_dict["GYM"] += amt

            # Fill in gross, total_deduction, net_pay from salary slip
            base = latest_slips[emp]
            row_dict["gross"] = base.gross_pay
            row_dict["total_deduction"] = base.total_deduction
            row_dict["net_pay"] = base.net_pay
            row_dict["company_pension"] = row_dict["basic"] * 0.11

            data.append(row_dict)

    return data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months