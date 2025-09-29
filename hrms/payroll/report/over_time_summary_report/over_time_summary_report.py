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
        {"label": "Job Title", "fieldname": "designation", "fieldtype": "Data", "width": 150},
        {"label": "Salary", "fieldname": "base", "fieldtype": "Currency", "width": 100},
        {"label": "OT 1.25", "fieldname": "ot_125", "fieldtype": "Float", "width": 80},
        {"label": "OT 1.50", "fieldname": "ot_150", "fieldtype": "Float", "width": 80},
        {"label": "OT 2.00", "fieldname": "ot_200", "fieldtype": "Float", "width": 80},
        {"label": "OT 2.50", "fieldname": "ot_250", "fieldtype": "Float", "width": 80},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 100},
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

    months = get_months_in_range(from_date, to_date)
    payment_order = ["Advance Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
    grouped = defaultdict(dict)

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
                SELECT
                    ss.employee,
                    ss.employee_name,
                    e.department,
                    e.branch,
                    e.designation,
                    e.grade,
                    e.name AS employee_id,
                    e.base,
                    od.ot_125,
                    od.ot_150,
                    od.ot_200,
                    od.ot_250,
                    asl.amount AS total_amount,
                    asl.payroll_date,
                    ss.end_date,
                    ss.payment_type,
                    DATE_FORMAT(asl.payroll_date, '%%Y-%%m') AS date
                FROM `tabAdditional Salary` asl
                INNER JOIN `tabOvertime detail` od
                    ON od.parent = asl.name
                INNER JOIN `tabSalary Slip` ss
                    ON ss.employee = asl.employee
                INNER JOIN `tabEmployee` e
                    ON e.name = asl.employee
                WHERE
                    asl.salary_component = 'OverTime'
                    AND asl.docstatus = 1
                    AND asl.payroll_date BETWEEN %(month_start)s AND %(month_end)s
                    {company_clause}
                    {employee_clause}
                    {branch_clause}
                    {department_clause}
                    {payment_type_clause}
                    {grade_clause}
                    {employment_type_clause}
                    AND (
                        COALESCE(od.ot_125,0) > 0 OR
                        COALESCE(od.ot_150,0) > 0 OR
                        COALESCE(od.ot_200,0) > 0 OR
                        COALESCE(od.ot_250,0) > 0
                    )
                ORDER BY asl.payroll_date ASC
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
            "month_end": month_end,
            "company":company
        }
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

        # For each employee, pick the latest salary slip by payment_type priority in this month
        latest_slips_per_emp = {}
        for row in data:
            emp = row.employee
            if emp not in latest_slips_per_emp:
                latest_slips_per_emp[emp] = row
            else:
                # Check if this row has higher priority payment_type than stored
                current_priority = payment_order.index(latest_slips_per_emp[emp].payment_type) if latest_slips_per_emp[emp].payment_type in payment_order else -1
                row_priority = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
                # Higher index means later priority, so pick one with lower index
                if row_priority < current_priority:
                    latest_slips_per_emp[emp] = row

        # Now sum base and OT only for employees who have OT in this month
        for emp, row in latest_slips_per_emp.items():
            dept = row.department or "No Department"
            emp_key = row.employee_id

            if emp_key not in grouped[dept]:
                grouped[dept][emp_key] = {
                    "employee_name": row.employee_name,
                    "employee": row.employee_id,
                    "designation": row.designation,
                    "base": row.base or 0,
                    "ot_125": row.ot_125 or 0,
                    "ot_150": row.ot_150 or 0,
                    "ot_200": row.ot_200 or 0,
                    "ot_250": row.ot_250 or 0,
                    "amount": row.total_amount or 0,
                    "date": row.date
                }

    # Prepare final output with department headers
    final_data = []
    for dept, employees in grouped.items():
        final_data.append({
            "employee": f"▶ {dept}",
            "employee_name": None,
            "base": None,
            "ot_125": None,
            "ot_150": None,
            "ot_200": None,
            "ot_250": None,
            "amount": None,
            "date": None
        })
        final_data.extend(employees.values())

    return final_data


def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months
