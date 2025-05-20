from collections import defaultdict
from datetime import timedelta
import frappe
from frappe.utils import getdate, add_months

def execute(filters=None):
	columns = get_columns()
	employee_rows = get_grouped_data(filters)
	return columns, employee_rows

def get_columns():
	return [
		{"label": "Name Of Staff", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": "TIN Number", "fieldname": "tin_number", "fieldtype": "Data", "width": 120},
		{"label": "Gross Salary", "fieldname": "gross_salary", "fieldtype": "Currency", "width": 150},
		{"label": "Tax on Gross Monthly Income", "fieldname": "income_tax", "fieldtype": "Currency", "width": 150},
		{"label": "Net Salary", "fieldname": "net_salary", "fieldtype": "Currency", "width": 150},
	]

def get_grouped_data(filters=None):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	company = filters.get("company")
	payment_type = filters.get("payment_type") 
	employee = filters.get("employee") 
	branch = filters.get("branch")
	department = filters.get("department")
	grade = filters.get("grade")
	employee_type = filters.get("employee_type")

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	months = get_months_in_range(from_date, to_date)
	grouped = defaultdict(list)

	for month in months:
		month_start = month.replace(day=1)
		month_end = add_months(month_start, 1) - timedelta(days=1)

		query = """
			SELECT 
				e.employee_tin_no,e.department,e.name AS employee, e.employee_name, e.department, e.designation,
				e.branch, e.grade, e.bank_name, e.employment_type,
				ss.name as salary_slip,ss.employee,ss.employee_name,
				ss.payment_type,ss.gross_pay,ss.net_pay,ss.end_date
			FROM `tabSalary Slip` ss
			LEFT JOIN `tabEmployee` e ON ss.employee = e.name
			WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
			  {company_clause}
              {employee_clause}
              {branch_clause}
			  {payment_type_clause}
              {department_clause}
              {grade_clause}
              {employee_type_clause}
			ORDER BY ss.end_date DESC
		""".format(
			company_clause="AND ss.company = %(company)s" if company else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
			payment_type_clause = "AND ss.payment_type = %(payment_type)s" if payment_type else "",
            department_clause="AND e.department = %(department)s" if department else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
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

		payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
		employee_latest_slip = {}
		net_salary_sum = defaultdict(float)

		for row in results:
			emp = row.employee
			net_salary_sum[emp] += row.net_pay

			current_type_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
			if emp not in employee_latest_slip:
				employee_latest_slip[emp] = row
			else:
				existing_type = employee_latest_slip[emp].payment_type
				existing_type_index = payment_order.index(existing_type) if existing_type in payment_order else -1
				if current_type_index > existing_type_index:
					employee_latest_slip[emp] = row

		for emp_id, slip in employee_latest_slip.items():
			income_tax = frappe.db.get_value("Salary Detail", {
				"parent": slip.salary_slip,
				"abbr": "IT",
				"parentfield": "deductions"
			}, "amount") or 0.0

			dept = slip.department or "No Department"
			grouped[dept].append({
				"employee_name": slip.employee_name,
				"tin_number": slip.employee_tin_no,
				"gross_salary": slip.gross_pay,
				"income_tax": income_tax,
				"net_salary": slip.net_pay
			})

	final_data = []
	for dept, rows in grouped.items():
		final_data.append({
			"employee_name": f"▶ {dept}",
			"tin_number": "",
			"gross_salary": None,
			"income_tax": None,
			"net_salary": None,
		})
		final_data.extend(rows)

	return final_data

def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months
