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
	payment_type = filters.get("payment_type")  # <-- added

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	months = get_months_in_range(from_date, to_date)
	grouped = defaultdict(list)

	for month in months:
		month = getdate(month)
		month_start = month.replace(day=1)
		month_end = (add_months(month_start, 1) - timedelta(days=1))

		conditions = ["ss.docstatus = 1", "ss.start_date BETWEEN %s AND %s"]
		params = [month_start, month_end]

		if company:
			conditions.append("ss.company = %s")
			params.append(company)

		if payment_type:
			conditions.append("ss.payment_type = %s")
			params.append(payment_type)

		query = f"""
			SELECT 
				ss.name as salary_slip,
				ss.employee,
				ss.employee_name,
				ss.payment_type,
				e.employee_tin_no,
				e.department,
				ss.gross_pay,
				ss.net_pay,
				ss.end_date
			FROM `tabSalary Slip` ss
			LEFT JOIN `tabEmployee` e ON ss.employee = e.name
			WHERE {' AND '.join(conditions)}
			ORDER BY ss.end_date DESC
		"""

		results = frappe.db.sql(query, tuple(params), as_dict=True)

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
