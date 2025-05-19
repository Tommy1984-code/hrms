# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	company_filter = filters.get("company") if filters else None
	company = frappe.get_doc("Company",company_filter) if company_filter else None

	company_data = {
		"company_bank_account":company.bank_ac_no if company else ""
	}

	for row in data:
		row.update(company_data)


	return columns, data

def get_columns():
	return [
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": "Bank Branch", "fieldname": "bank", "fieldtype": "Data", "width": 220},
		{"label": "Account Number", "fieldname": "bank_ac_no", "fieldtype": "Data", "width": 150},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 150},
	]

def get_data(filters=None):
	
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	employee = filters.get("employee")
	payment_type = filters.get("payment_type")
	branch = filters.get("branch")
	department = filters.get("department")
	grade = filters.get("grade")
	employee_type = filters.get("employee_type")
	bank = filters.get("bank")

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	months = get_months_in_range(from_date, to_date)
	latest_slips = {}

	for month in months:
		month_start = month.replace(day=1)
		month_end = (add_months(month_start, 1) - timedelta(days=1))

		payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

		# Dynamically build WHERE clauses
		clauses = []
		if company:
			clauses.append("ss.company = %(company)s")
		if employee:
			clauses.append("ss.employee = %(employee)s")
		if payment_type:
			clauses.append("ss.payment_type = %(payment_type)s")
		if branch:
			clauses.append("e.branch = %(branch)s")
		if department:
			clauses.append("e.department = %(department)s")
		if grade:
			clauses.append("e.grade = %(grade)s")
		if employee_type:
			clauses.append("e.employment_type = %(employee_type)s")
		if bank:
			clauses.append("ss.bank_name = %(bank)s")

		where_clause = " AND " + " AND ".join(clauses) if clauses else ""

		query = f"""
			SELECT 
				ss.name as salary_slip, ss.employee, ss.net_pay, ss.posting_date,
				e.employee_name, e.bank_name, e.bank_ac_no, e.department, e.designation,
				e.branch, e.employment_type,
				ss.payment_type
			FROM `tabSalary Slip` ss
			LEFT JOIN `tabEmployee` e ON ss.employee = e.name
			WHERE ss.docstatus = 1
				AND ss.start_date BETWEEN %(month_start)s AND %(month_end)s
				{where_clause}
			ORDER BY ss.posting_date DESC
		"""

		params = {
			"month_start": month_start,
			"month_end": month_end
		}
		if company:
			params["company"] = company
		if employee:
			params["employee"] = employee
		if payment_type:
			params["payment_type"] = payment_type
		if branch:
			params["branch"] = branch
		if department:
			params["department"] = department
		if grade:
			params["grade"] = grade
		if employee_type:
			params["employee_type"] = employee_type
		if bank:
			params["bank"] = bank

		results = frappe.db.sql(query, params, as_dict=True)

		for row in results:
			emp = row.employee
			current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1

			if emp not in latest_slips:
				latest_slips[emp] = row
			else:
				existing_index = payment_order.index(latest_slips[emp].payment_type) \
					if latest_slips[emp].payment_type in payment_order else -1

				if current_index > existing_index:
					latest_slips[emp] = row

	data = []
	for row in latest_slips.values():
		data.append({
			"employee_name": row.employee_name,
			"bank": row.bank_name,
			"bank_ac_no": row.bank_ac_no,
			"amount": row.net_pay
		})

	return data

def get_months_in_range(start_date, end_date):
	months = []
	current_month = start_date.replace(day=1)

	while current_month <= end_date:
		months.append(current_month)
		current_month = add_months(current_month, 1)

	return months
