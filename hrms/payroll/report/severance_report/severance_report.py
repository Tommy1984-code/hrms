# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta
import calendar


def execute(filters=None):
	
	employee_filter = filters.get("employee") if filters else None
	columns = get_columns(employee_filter)
	data = get_data(filters)

	employee_filter = filters.get("employee") if filters else None

	employee_termination_data = {}

	if employee_filter:
		termination = frappe.get_value(
			"Employee Termination",
			{"employee": employee_filter},
			["employee_name", "date_of_employment", "termination_date", "total_severance", "severance_tax", "net_severance"],
			as_dict=True
		)

		if termination:
			employee_termination_data = {
				"employee_name": termination.employee_name,
				"date_of_employment": termination.date_of_employment,
				"termination_date": termination.termination_date,
				"total_severance": termination.total_severance,
				"severance_tax": termination.severance_tax,
				"net_severance": termination.net_severance
			}

	# Apply data to each row
	for row in data:
		row.update(employee_termination_data)

	return columns, data

def get_columns(employee_filter):

	if employee_filter:
		return [
			{"label":"From", "fieldname": "from_date", "fieldtype": "Date", "width": 200},
			{"label": "To", "fieldname": "to_date", "fieldtype": "Date", "width": 200},
			{"label":"Basic Salary", "fieldname": "basic_salary", "fieldtype": "Currency", "width": 150},
			{"label": "Rate", "fieldname": "rate", "fieldtype": "Data", "width": 150},
			{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 150},
		]
	else:
		# Columns when NO employee is selected
		return [
			{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
			{"label": "Date of Employment", "fieldname": "date_of_employment", "fieldtype": "Date", "width": 180},
			{"label": "Termination Date", "fieldname": "termination_date", "fieldtype": "Date", "width": 180},
			{"label": "Total Severance", "fieldname": "total_severance", "fieldtype": "Currency", "width": 150},
			{"label": "Severance Tax", "fieldname": "severance_tax", "fieldtype": "Currency", "width": 150},
			{"label": "Net Severance", "fieldname": "net_severance", "fieldtype": "Currency", "width": 150},
		]

def get_data(filters):
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	employee = filters.get("employee")

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	data = []
	months = get_months_in_range(from_date, to_date)

	for month in months:
		month_start = month.replace(day=1)
		month_end = add_months(month_start, 1) - timedelta(days=1)

		if employee:
			# Detailed view for selected employee
			query = """
				SELECT
					st.date_from,
					st.date_to,
					et.basic_salary,
					st.percent AS rate,
					st.amount
				FROM
					`tabEmployee Termination` et
				JOIN
					`tabSeverance Detail` st ON st.parent = et.name
				WHERE
					et.termination_date BETWEEN %(month_start)s AND %(month_end)s
					AND et.employee = %(employee)s
					AND et.company = %(company)s
					AND st.amount > 0
			"""

			params = {
				"month_start": month_start,
				"month_end": month_end,
				"employee": employee,
				"company":company
			}

			results = frappe.db.sql(query, params, as_dict=True)

			for row in results:
				from_str = f"{calendar.month_abbr[row.date_from.month]} {row.date_from.year}"
				to_str = f"{calendar.month_abbr[row.date_to.month]} {row.date_to.year}"

				data.append({
					"year": row.date_from.year,
					"from_date": from_str,
					"to_date": to_str,
					"basic_salary": row.basic_salary,
					"rate": f"{row.rate}%",
					"amount": row.amount
				})

		else:
			# Summary view for all employees
			query = """
				SELECT
					et.employee,
					et.employee_name,
					et.date_of_employment,
					et.termination_date,
					et.total_severance,
					et.severance_tax,
					et.net_severance
				FROM
					`tabEmployee Termination` et
				WHERE
					et.termination_date BETWEEN %(month_start)s AND %(month_end)s
					AND et.company = %(company)s
					AND et.total_severance > 0
			"""

			params = {
				"month_start": month_start,
				"month_end": month_end,
				"company":company
			}

			results = frappe.db.sql(query, params, as_dict=True)

			for row in results:
				# Ensure no duplicate employees
				if not any(d.get("employee") == row.employee for d in data):
					data.append({
						"employee": row.employee,
						"employee_name": row.employee_name,
						"date_of_employment": row.date_of_employment,
						"termination_date": row.termination_date,
						"total_severance": row.total_severance,
						"severance_tax": row.severance_tax,
						"net_severance": row.net_severance
					})

	# Sort the detailed data only if employee is selected
	if employee:
		data.sort(key=lambda x: (x["year"], list(calendar.month_abbr).index(x["from_date"].split(" ")[0])))

	return data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months