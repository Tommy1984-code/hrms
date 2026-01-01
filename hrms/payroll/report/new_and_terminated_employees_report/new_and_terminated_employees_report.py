# Copyright (c) 2026, Frappe Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months


def execute(filters=None):
	filters = filters or {}
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Data", "width": 200},
		{"label": "Full Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": "Sex", "fieldname": "gender", "fieldtype": "Data", "width": 120},
		{"label": "Job Title", "fieldname": "designation", "fieldtype": "Data", "width": 150},
		{"label": "Date of Hire (G.C)", "fieldname": "date_of_hire", "fieldtype": "Date", "width": 120},
		{"label": "Date of Birth", "fieldname": "date_of_birth", "fieldtype": "Date", "width": 120},
		{"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 200},
		{"label": "Grade", "fieldname": "grade", "fieldtype": "Data", "width": 100},
	]

	# Show relieving date ONLY for terminated employees
	if filters.get("employee_status_filter") == "Terminated":
		columns.append({
			"label": "Relieving Date",
			"fieldname": "relieving_date",
			"fieldtype": "Date",
			"width": 120
		})

	return columns


def get_data(filters):
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	status_filter = filters.get("employee_status_filter")

	employee_filters = {
		"company": company
	}

	# Employee status filter
	if status_filter == "New":
		employee_filters["status"] = "Active"
	elif status_filter == "Terminated":
		employee_filters["status"] = "Left"

	# Optional filters
	if filters.get("employee"):
		employee_filters["name"] = filters.get("employee")
	if filters.get("department"):
		employee_filters["department"] = filters.get("department")
	if filters.get("grade"):
		employee_filters["grade"] = filters.get("grade")
	if filters.get("employee_type"):
		employee_filters["employment_type"] = filters.get("employee_type")
	if filters.get("designation"):
		employee_filters["designation"] = filters.get("designation")
	if filters.get("branch"):
		employee_filters["branch"] = filters.get("branch")

	employees = frappe.get_all(
		"Employee",
		filters=employee_filters,
		fields=[
			"name as employee_id",
			"employee_name",
			"gender",
			"designation",
			"date_of_joining as date_of_hire",
			"date_of_birth",
			"department",
			"grade",
			"relieving_date"
		],
		order_by="department asc, employee_name asc"
	)

	# STRICT date logic (FIXED)
	filtered_employees = []

	for emp in employees:
		if status_filter == "New":
			# ONLY employees hired within selected date range
			if emp.date_of_hire and from_date <= emp.date_of_hire <= to_date:
				filtered_employees.append(emp)

		elif status_filter == "Terminated":
			# ONLY employees relieved within selected date range
			if emp.relieving_date and from_date <= emp.relieving_date <= to_date:
				filtered_employees.append(emp)

	data = []
	current_department = None

	for emp in filtered_employees:
		department = emp.department or "No Department"

		# Department header
		if department != current_department:
			data.append({
				"employee_id": f"▶ {department}"
			})
			current_department = department

		row = {
			"employee_id": emp.employee_id,
			"employee_name": emp.employee_name,
			"gender": emp.gender,
			"designation": emp.designation,
			"date_of_hire": emp.date_of_hire,
			"date_of_birth": emp.date_of_birth,
			"section": emp.department,
			"grade": emp.grade
		}

		if status_filter == "Terminated":
			row["relieving_date"] = emp.relieving_date

		data.append(row)

	return data


def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months
