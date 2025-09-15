# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months, formatdate
from datetime import timedelta
from collections import defaultdict


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
    return [
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Data", "options": "Employee", "width": 150},
        {"label": "Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Salary Inc", "fieldname": "salary_base", "fieldtype": "Currency", "width": 120},
        {"label": "Tax", "fieldname": "salary_tax", "fieldtype": "Currency", "width": 120},
        {"label": "Pension", "fieldname": "pension", "fieldtype": "Currency", "width": 100},
        {"label": "Salary Advance", "fieldname": "salary_advance", "fieldtype": "Currency", "width": 120},
        {"label": "Loan", "fieldname": "loan", "fieldtype": "Currency", "width": 100},
        {"label": "GYM", "fieldname": "gym", "fieldtype": "Currency", "width": 100},
        {"label": "Commission Deduction", "fieldname": "commission", "fieldtype": "Currency", "width": 150},
        {"label": "Cost Sharing", "fieldname": "cost_sharing", "fieldtype": "Currency", "width": 120},
        {"label": "Court", "fieldname": "court", "fieldtype": "Currency", "width": 100},
        {"label": "Bank", "fieldname": "bank", "fieldtype": "Currency", "width": 100},
        {"label": "Credit Purchase", "fieldname": "credit_purchase", "fieldtype": "Currency", "width": 130},
        {"label": "Saving", "fieldname": "saving", "fieldtype": "Currency", "width": 100},
        {"label": "Penalty", "fieldname": "penalty", "fieldtype": "Currency", "width": 100},
        {"label": "Medical", "fieldname": "medical", "fieldtype": "Currency", "width": 100},
        {"label": "Total", "fieldname": "total", "fieldtype": "Currency", "width": 120},
    ]



def get_data(filters):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    mode_of_payment = filters.get("mode_of_payment")
    employee = filters.get("employee")
    payment_type = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")
    bank = filters.get("bank")

    months = get_months_in_range(from_date, to_date)
    payment_order = ["Advance Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    all_filtered_rows = []

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
            SELECT e.name AS employee, e.employee_name, e.department, e.designation, e.branch, e.grade, e.bank_name, e.employment_type,
                   ss.name AS salary_slip, ss.gross_pay, ss.net_pay, ss.mode_of_payment, ss.payment_type,
                   ss.total_deduction, ss.end_date, ss.start_date,
                   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
              {company_clause}
              {payment_mode_clause}
              {employee_clause}
              {payment_type_clause}
              {branch_clause}
              {department_clause}
              {grade_clause}
              {job_title_clause}
              {employee_type_clause}
              {bank_clause}
            ORDER BY ss.end_date DESC
        """.format(
            payment_mode_clause="AND ss.mode_of_payment = %(mode_of_payment)s" if mode_of_payment else "",
            company_clause="AND ss.company = %(company)s" if company else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
            department_clause="AND e.department = %(department)s" if department else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
            job_title_clause="AND e.designation = %(job_title)s" if job_title else "",
            employee_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else "",
            bank_clause="AND ss.bank_name = %(bank)s" if bank else ""
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company":company
        }

        for field in [
            "mode_of_payment", "employee", "payment_type", "branch", "department",
            "grade", "job_title", "employee_type", "bank"
        ]:
            value = locals().get(field)
            if value:
                params[field] = value

        results = frappe.db.sql(query, params, as_dict=True)

        # Select latest salary slip per employee for the month based on payment type
        latest_slips = {}
        for row in results:
            emp = row.employee
            month_key = f"{emp}_{row.end_date.strftime('%Y-%m')}"
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
            existing = latest_slips.get(month_key)

            if not existing or current_index > payment_order.index(existing.payment_type):
                latest_slips[month_key] = row

        selected_slip_names = {row.salary_slip for row in latest_slips.values()}
        filtered_rows = [row for row in results if row.salary_slip in selected_slip_names]
        all_filtered_rows.extend(filtered_rows)

   

    grouped = defaultdict(lambda: {
        "salary_base": 0, "salary_tax": 0, "pension": 0, "salary_advance": 0,
        "loan": 0, "gym": 0, "commission": 0, "cost_sharing": 0,
        "court": 0, "bank": 0, "credit_purchase": 0, "saving": 0,
        "penalty": 0, "medical": 0, "other_earnings": 0, "other_deductions": 0,
        "total": 0
    })

    for row in all_filtered_rows:
        key = (row.employee, row.department)
        abbr = row.abbr
        amount = row.amount or 0
        pf = row.parentfield
        data = grouped[key]
        data["employee"] = row.employee
        full_name = row.employee_name or ""
        name_parts = full_name.split()
        short_name = " ".join(name_parts[:2]) if len(name_parts) >= 2 else full_name
        data["employee_name"] = short_name

        if abbr in ("B", "VB"):
            data["salary_base"] += amount
        elif abbr == "IT":
            data["salary_tax"] += amount
        elif abbr == "PS":
            data["pension"] += amount
        elif abbr == "APNI":
            data["salary_advance"] += amount
        elif abbr == "LN":
            data["loan"] += amount
        elif abbr == "GM":
            data["gym"] += amount
        elif abbr == "CD":
            data["commission"] += amount
        elif abbr == "csl":
            data["cost_sharing"] += amount
        elif abbr == "CRT":
            data["court"] += amount
        elif abbr == "BNK":
            data["bank"] += amount
        elif abbr == "CP":
            data["credit_purchase"] += amount
        elif abbr == "SVG":
            data["saving"] += amount
        elif abbr == "PNLT":
            data["penalty"] += amount
        elif abbr == "HL":
            data["medical"] += amount

    for key, data in grouped.items():
        data["total"] = (
            data["salary_tax"] + data["salary_advance"] + data["loan"] +
            data["gym"] + data["commission"] + data["cost_sharing"] + data["court"] +
            data["bank"] + data["credit_purchase"] + data["saving"] +
            data["penalty"] + data["medical"]
        )

    department_data = defaultdict(list)
    for (employee, dept), data in grouped.items():
        department_data[dept or "No Department"].append(data)

    final_data = []
    for dept, rows in sorted(department_data.items()):
        final_data.append({
            "employee": f"▶ {dept}",
            "employee_name": "",
            "salary_tax": None, "pension": None, "salary_advance": None,
            "loan": None, "gym": None, "commission": None,
            "cost_sharing": None, "court": None, "bank": None,
            "credit_purchase": None, "saving": None,
            "penalty": None, "medical": None, "salary_base": None,
            "other_earnings": None, "other_deductions": None, "total": None
        })
        final_data.extend(rows)

    return final_data



def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date.replace(day=1)

    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)

    return months