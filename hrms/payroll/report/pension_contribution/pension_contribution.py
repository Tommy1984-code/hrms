# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict



def execute(filters=None):
	columns = get_columns()
	employee_rows = get_grouped_data(filters)
	
     
	return columns, employee_rows


def get_columns():
	return[

		{"label":"Name Of Staff","fieldname":"employee_name","fieldtype":"Data","width": 200},
		{"label":"TIN Number","fieldname":"tin_number","fieldtype":"Data","width": 120},
		{"label":"Employee Contribution","fieldname":"employee_pension","fieldtype":"Currency","width": 150},
		{"label":"Company Contribution ","fieldname":"company_pension","fieldtype":"Currency","width": 150},
		{"label":"Total in Birr","fieldname":"total_pension","fieldtype":"Currency","width": 150},
	]


def get_grouped_data(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")
    employee = filters.get("employee")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    grouped = defaultdict(list)
    employee_totals = {}

    for month in months:
        month = getdate(month)
        month_start = month.replace(day=1)
        month_end = (add_months(month_start, 1) - timedelta(days=1))

        # Fetch latest salary slip per employee for this month
        query = """
            SELECT
                ss.name as salary_slip,
                ss.employee,
                e.employee_name,
                e.employee_tin_no,
                e.department,
                d.department_name,
                ss.end_date
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            LEFT JOIN `tabDepartment` d ON d.name = e.department
            WHERE ss.start_date <= %(month_end)s
              AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
              {company_clause}
              {employee_clause}
              {branch_clause}
              {department_clause}
              {grade_clause}
              {job_title_clause}
              {employee_type_clause}
            ORDER BY ss.end_date DESC
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
            department_clause="AND e.department = %(department)s" if department else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
            job_title_clause="AND e.designation = %(job_title)s" if job_title else "",
            employee_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else "",
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company": company,
        }

        optional_fields = ["employee", "branch", "department", "grade", "job_title", "employee_type"]
        for field in optional_fields:
            value = locals().get(field)
            if value:
                params[field] = value

        salary_slips = frappe.db.sql(query, params, as_dict=True)

        seen_employees = set()

        for slip in salary_slips:
            emp = slip.employee
            if emp in seen_employees:
                continue  # only latest per employee for this month
            seen_employees.add(emp)

            # Fetch BASIC or VBASIC
            base = frappe.db.sql("""
                SELECT amount FROM `tabSalary Detail`
                WHERE parent = %s AND abbr IN ('B', 'VB') AND parentfield = 'earnings'
                ORDER BY amount DESC LIMIT 1
            """, (slip.salary_slip,), as_dict=True)

            if not base:
                continue

            base_salary = base[0].amount
            emp_pension = base_salary * 0.07
            comp_pension = base_salary * 0.11
            total_pension = emp_pension + comp_pension

            if emp not in employee_totals:
                employee_totals[emp] = {
                    "employee_name": slip.employee_name,
                    "tin_number": slip.employee_tin_no,
                    "department_name": slip.department_name or "No Department",
                    "employee_pension": 0,
                    "company_pension": 0,
                    "total_pension": 0
                }

            employee_totals[emp]["employee_pension"] += emp_pension
            employee_totals[emp]["company_pension"] += comp_pension
            employee_totals[emp]["total_pension"] += total_pension

    # Final formatting
    for emp_data in employee_totals.values():
        dept = emp_data["department_name"]
        grouped[dept].append({
            "employee_name": emp_data["employee_name"],
            "tin_number": emp_data["tin_number"],
            "employee_pension": emp_data["employee_pension"],
            "company_pension": emp_data["company_pension"],
            "total_pension": emp_data["total_pension"],
        })

    final_data = []
    for dept, employees in grouped.items():
        final_data.append({
            "employee_name": f"▶ {dept}",
            "tin_number": "",
            "employee_pension": None,
            "company_pension": None,
            "total_pension": None,
        })
        final_data.extend(employees)

    return final_data

def get_base_from_salary_slip(employee_id, month):
    # Fetch BASIC or VBASIC for a specific month
    for abbr in ["B", "VB"]:
        result = frappe.db.sql("""
            SELECT sd.amount
            FROM `tabSalary Slip` ss
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.employee = %s
                AND ss.start_date <= %s
                AND ss.end_date >= %s
                AND ss.docstatus = 1
                AND sd.abbr = %s
                AND sd.parentfield = 'earnings'
            ORDER BY ss.end_date DESC
            LIMIT 1
        """, (employee_id, month, month, abbr), as_dict=True)

        if result:
            return result[0].amount

    return 0

def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date

    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)

    return months