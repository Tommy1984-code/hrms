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

	query = """
		SELECT 
			e.employee_tin_no, e.department, e.name AS employee, e.employee_name,
			ss.name AS salary_slip, ss.payment_type, ss.gross_pay, ss.net_pay, ss.end_date
		FROM `tabSalary Slip` ss
		LEFT JOIN `tabEmployee` e ON ss.employee = e.name
		WHERE ss.start_date >= %(from_date)s AND ss.end_date <= %(to_date)s
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
		payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
		department_clause="AND e.department = %(department)s" if department else "",
		grade_clause="AND e.grade = %(grade)s" if grade else "",
		employee_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else "",
	)

	params = {
		"from_date": getdate(from_date),
		"to_date": getdate(to_date),
		"company": company
	}
	for key in ["employee", "branch", "payment_type", "department", "grade", "employee_type"]:
		if filters.get(key):
			params[key] = filters.get(key)

	results = frappe.db.sql(query, params, as_dict=True)
	payment_order = ["First Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
	grouped = defaultdict(list)

	# Organize slips per employee
	employee_data = defaultdict(list)
	for row in results:
		employee_data[row.employee].append(row)

	final_result = []

	for emp, slips in employee_data.items():
		tin = slips[0].employee_tin_no
		name = slips[0].employee_name
		dept = slips[0].department or "No Department"
		net = 0
		gross = 0
		income_tax = 0

		if payment_type:
			# Sum all of the given type
			for s in slips:
				if s.payment_type == payment_type:
					gross += s.gross_pay
					net += s.net_pay
					tax = frappe.db.get_value("Salary Detail", {
						"parent": s.salary_slip,
						"abbr": "IT",
						"parentfield": "deductions"
					}, "amount") or 0.0
					income_tax += tax
		else:
			# For each month, pick the best (latest by payment type priority)
			best_slip_by_month = {}
			for s in slips:
				month_key = s.end_date.strftime("%Y-%m")
				if month_key not in best_slip_by_month:
					best_slip_by_month[month_key] = s
				else:
					current_priority = payment_order.index(s.payment_type) if s.payment_type in payment_order else -1
					existing_priority = payment_order.index(best_slip_by_month[month_key].payment_type) if best_slip_by_month[month_key].payment_type in payment_order else -1
					if current_priority > existing_priority:
						best_slip_by_month[month_key] = s

			for slip in best_slip_by_month.values():
				gross += slip.gross_pay
				net += slip.net_pay
				tax = frappe.db.get_value("Salary Detail", {
					"parent": slip.salary_slip,
					"abbr": "IT",
					"parentfield": "deductions"
				}, "amount") or 0.0
				income_tax += tax

		grouped[dept].append({
			"employee_name": name,
			"tin_number": tin,
			"gross_salary": gross,
			"income_tax": income_tax,
			"net_salary": net
		})

	# Final display
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
