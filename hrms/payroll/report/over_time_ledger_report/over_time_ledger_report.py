# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict
from datetime import timedelta
import frappe
from frappe.utils import getdate, add_months


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
    return [
        {"label": "Employee ID", "fieldname": "employee", "fieldtype":"Data","width": 150},
        {"label": "Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 90},
        {"label": "OT 1.25", "fieldname": "ot_1_25", "fieldtype": "Float", "width": 80},
        {"label": "Amount 1.25", "fieldname": "amount_1_25", "fieldtype": "Currency", "width": 90},
        {"label": "OT 1.5", "fieldname": "ot_1_5", "fieldtype": "Float", "width": 80},
        {"label": "Amount 1.5", "fieldname": "amount_1_5", "fieldtype": "Currency", "width": 90},
        {"label": "OT 2.0", "fieldname": "ot_2_0", "fieldtype": "Float", "width": 80},
        {"label": "Amount 2.0", "fieldname": "amount_2_0", "fieldtype": "Currency", "width": 90},
        {"label": "OT 2.5", "fieldname": "ot_2_5", "fieldtype": "Float", "width": 80},
        {"label": "Amount 2.5", "fieldname": "amount_2_5", "fieldtype": "Currency", "width": 90},
       
    ]

def get_data(filters):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    employee = filters.get("employee")
    payment_type = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    employee_type = filters.get("employee_type")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
    months = get_months_in_range(from_date, to_date)

    final_data = []
    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
            SELECT
                ss.name as salary_slip,
                ss.employee,
                ss.employee_name,
                ss.payment_type,
                ss.start_date AS date,
                e.department,
                e.branch,
                e.designation,
                e.grade,
                e.name AS employee_id,
                e.base,
                asl.working_hour,
                asl.rate,
                asl.amount
            FROM `tabSalary Slip` ss
            INNER JOIN `tabAdditional Salary` asl ON
                asl.employee = ss.employee
                AND asl.salary_component = 'OverTime'
                AND asl.docstatus = 1
            INNER JOIN `tabEmployee` e ON e.name = ss.employee
            WHERE
                ss.docstatus = 1
                AND ss.start_date <= %(month_end)s
                AND ss.end_date >= %(month_start)s
                {company_clause}
                {employee_clause}
                {branch_clause}
                {department_clause}
                {payment_type_clause}
                {grade_clause}
                {employment_type_clause}
                AND asl.working_hour > 0
            ORDER BY ss.end_date DESC
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
            department_clause="AND e.department = %(department)s" if department else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
            employment_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else ""
        )

        params = {
            "month_start": month_start,
            "month_end": month_end
        }
        if company:
            params["company"] = company
        if employee:
            params["employee"] = employee
        if branch:
            params["branch"] = branch
        if department:
            params["department"] = department
        if payment_type:
            params["payment_type"] = payment_type
        if grade:
            params["grade"] = grade
        if employee_type:
            params["employee_type"] = employee_type

        data = frappe.db.sql(query, params, as_dict=True)

        # Keep only the latest salary slip per employee per month by payment_type priority
        latest_slips = {}
        for row in data:
            emp = row.employee
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
            if emp not in latest_slips or current_index > payment_order.index(latest_slips[emp].payment_type):
                latest_slips[emp] = row

        # Process each latest slip
        for row in latest_slips.values():
            rate = float(row.rate) if row.rate else 0
            wh = row.working_hour or 0
            amt = row.amount or 0

            final_data.append({
                "employee": row.employee,
                "employee_name": row.employee_name,
                "date": row.date,
                "designation": row.designation,
                "ot_1_25": wh if rate == 1.25 else 0,
                "amount_1_25": amt if rate == 1.25 else 0,
                "ot_1_5": wh if rate == 1.5 else 0,
                "amount_1_5": amt if rate == 1.5 else 0,
                "ot_2_0": wh if rate == 2.0 else 0,
                "amount_2_0": amt if rate == 2.0 else 0,
                "ot_2_5": wh if rate == 2.5 else 0,
                "amount_2_5": amt if rate == 2.5 else 0,
            })

    return final_data


def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months
