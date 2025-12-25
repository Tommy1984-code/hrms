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
        {"label": "OT 1.5", "fieldname": "ot_1_5", "fieldtype": "Float", "width": 80},
        {"label": "Amount 1.5", "fieldname": "amount_1_5", "fieldtype": "Currency", "width": 90},
        {"label": "OT 1.75", "fieldname": "ot_1_75", "fieldtype": "Float", "width": 80},
        {"label": "Amount 1.75", "fieldname": "amount_1_75", "fieldtype": "Currency", "width": 90},       
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

    payment_order = ["First Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
    months = get_months_in_range(from_date, to_date)

    employee_data_map = {}

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
                SELECT
                    ss.name AS salary_slip,
                    ss.employee,
                    ss.employee_name,
                    ss.payment_type,
                    e.department,
                    e.branch,
                    e.designation,
                    e.grade,
                    e.name AS employee_id,
                    od.ot_150,
                    od.ot_175,
                    od.ot_200,
                    od.ot_250,
                    asl.amount AS total_amount,
                    asl.base_salary,
                    asl.payroll_date,
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
                        
                        COALESCE(od.ot_150,0) > 0 OR
                        COALESCE(od.ot_175,0) > 0 OR
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

        latest_slips = {}
        for row in data:
            emp = row.employee
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
            if emp not in latest_slips or current_index > payment_order.index(latest_slips[emp].payment_type):
                latest_slips[emp] = row

        for row in latest_slips.values():
            rate = float(row.rate) if row.rate else 0
            wh = row.working_hour or 0
            amt = row.amount or 0


            for row in data:
                base_salary = float(row.base_salary or 0)
                if row.employee not in employee_data_map:
                    employee_data_map[row.employee] = {
                        "employee": row.employee,
                        "employee_name": row.employee_name,
                        "date": row.date,
                        "designation": row.designation,
                        "ot_1_5": row.ot_150 or 0,
                        "amount_1_5":((base_salary / 208) * (row.ot_150 or 0) * 1.5) if row.ot_150 else 0,
                        "ot_1_75": row.ot_175 or 0,
                        "amount_1_75": ((base_salary / 208) * (row.ot_175 or 0) * 1.75) if row.ot_175 else 0,
                        "ot_2_0": row.ot_200 or 0,
                        "amount_2_0": ((base_salary / 208) * (row.ot_200 or 0) * 2.0) if row.ot_200 else 0,
                        "ot_2_5": row.ot_250 or 0,
                        "amount_2_5": ((base_salary / 208) * (row.ot_250 or 0) * 2.5) if row.ot_250 else 0,
                    }
           
            if rate == 1.5:
                employee_data_map[row.employee]["ot_1_5"] += wh
                employee_data_map[row.employee]["amount_1_5"] += ((base_salary / 208) * (row.ot_150 or 0) * 1.5) if row.ot_150 else 0
            elif rate == 1.75:
                employee_data_map[row.employee]["ot_1_75"] += wh
                employee_data_map[row.employee]["amount_1_75"] +=  ((base_salary / 208) * (row.ot_175 or 0) * 1.75) if row.ot_175 else 0
            elif rate == 2.0:
                employee_data_map[row.employee]["ot_2_0"] += wh
                employee_data_map[row.employee]["amount_2_0"] += ((base_salary / 208) * (row.ot_200 or 0) * 2.0) if row.ot_200 else 0
            elif rate == 2.5:
                employee_data_map[row.employee]["ot_2_5"] += wh
                employee_data_map[row.employee]["amount_2_5"] += ((base_salary / 208) * (row.ot_250 or 0) * 2.5) if row.ot_250 else 0

    final_data = list(employee_data_map.values())
    return final_data


def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months
