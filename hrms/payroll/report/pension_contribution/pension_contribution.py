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

    for month in months:
        month = getdate(month)
        month_start = month.replace(day=1)
        month_end = (add_months(month_start, 1) - timedelta(days=1))

        query = """
            SELECT
                e.employee_name,
                e.employee_tin_no,
                e.department,
                d.department_name,
                sd.amount AS basic_salary,
                ss.end_date,
                ss.employee
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            LEFT JOIN `tabDepartment` d ON d.name = e.department
            WHERE ss.start_date <= %(month_end)s
                AND ss.end_date >= %(month_start)s
                AND ss.docstatus = 1
                AND sd.abbr IN ('B', 'VB')
              {company_clause}
              {employee_clause}
              {branch_clause}
              {department_clause}
              {grade_clause}
              {employee_type_clause}
              
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
            "company" :company
        }

        optional_fields = [
            "employee",
            "payment_type",
            "branch",
            "department",
            "grade",
            "job_title",
            "employee_type",
        ]

        for field in optional_fields:
            value = locals().get(field)
            if value:
                params[field] = value

        results = frappe.db.sql(query, params, as_dict=True)
 
        # Group results by employee to ensure we're getting the latest salary slip
        employee_latest_slip = {}

        for row in results:
            employee_id = row.employee
            if employee_id not in employee_latest_slip:
                # For each employee, store the first result we encounter (latest based on end_date)
                employee_latest_slip[employee_id] = row
            else:
                # If this result has a later end_date, update the entry
                existing_row = employee_latest_slip[employee_id]
                if row.end_date > existing_row['end_date']:
                    employee_latest_slip[employee_id] = row

        # Now process the latest salary slips
        for row in employee_latest_slip.values():
            department_name = row.department_name or "No Department"
            base_salary = row.basic_salary
            employee_pension = base_salary * 0.07
            company_pension = base_salary * 0.11
            total_pension = employee_pension + company_pension

            grouped[department_name].append({
                "employee_name": row.employee_name,
                "tin_number": row.employee_tin_no,
                "employee_pension": employee_pension,
                "company_pension": company_pension,
                "total_pension": total_pension,
                "month": month.strftime("%B %Y")
            })

    # Flatten into a list, inserting a row with only department as header
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