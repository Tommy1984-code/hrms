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

from collections import defaultdict
from datetime import timedelta
from frappe.utils import getdate, add_months

def get_data(filters):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    employee = filters.get("employee")
    payment_type = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    employee_type = filters.get("employee_type")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
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
                sd.amount,
                ss.end_date,
                ss.payment_type,
                asl.working_hour,
                asl.rate,
                COALESCE(asl.payroll_date, asl.from_date) AS date
            FROM `tabSalary Slip` ss
            INNER JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            LEFT JOIN `tabEmployee` e ON e.name = ss.employee
            LEFT JOIN `tabAdditional Salary` asl ON
                asl.employee = ss.employee
                AND asl.salary_component = 'OverTime'
                AND asl.docstatus = 1
                AND (
                    (asl.payroll_date BETWEEN %(month_start)s AND %(month_end)s)
                    OR (
                        asl.from_date IS NOT NULL AND asl.to_date IS NOT NULL
                        AND asl.from_date <= %(month_end)s
                        AND asl.to_date >= %(month_start)s
                    )
                )
            WHERE
                ss.docstatus = 1
                AND sd.salary_component = 'OverTime'
                AND ss.start_date <= %(month_end)s
                AND ss.end_date >= %(month_start)s
                {employee_clause}
                {branch_clause}
                {department_clause}
                {payment_type_clause}
                {grade_clause}
                {employment_type_clause}
            ORDER BY ss.employee, ss.end_date DESC, 
                FIELD(ss.payment_type, '{payment_order_str}')
        """.format(
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
            department_clause="AND e.department = %(department)s" if department else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
            employment_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else "",
            payment_order_str="','".join(payment_order)
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
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
                    "base": 0,
                    "ot_125": 0,
                    "ot_150": 0,
                    "ot_200": 0,
                    "ot_250": 0,
                    "amount": 0,
                    "date": None
                }

            # Add base salary for this month (only for employees with OT this month)
            grouped[dept][emp_key]["base"] += row.base or 0

            # Accumulate OT hours by rate
            rate = float(row.rate) if row.rate else 0
            working_hour = row.working_hour or 0

            if rate == 1.25:
                grouped[dept][emp_key]["ot_125"] += working_hour
            elif rate == 1.5:
                grouped[dept][emp_key]["ot_150"] += working_hour
            elif rate == 2.0:
                grouped[dept][emp_key]["ot_200"] += working_hour
            elif rate == 2.5:
                grouped[dept][emp_key]["ot_250"] += working_hour

            # Accumulate OT amount
            grouped[dept][emp_key]["amount"] += row.amount or 0

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
