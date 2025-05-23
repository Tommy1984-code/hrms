# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta
import calendar


def execute(filters=None):
	columns = get_columns()
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

def get_columns():
    return [
        {"label":"From", "fieldname": "from_date", "fieldtype": "Date", "width": 200},
        {"label": "To", "fieldname": "to_date", "fieldtype": "Date", "width": 200},
        {"label":"Basic Salary", "fieldname": "basic_salary", "fieldtype": "Currency", "width": 150},
        {"label": "Rate", "fieldname": "rate", "fieldtype": "Data", "width": 150},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 150},
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
				{employee_clause}
				{company_clause}
		""".format(
			employee_clause="AND et.employee = %(employee)s" if employee else "",
			company_clause="AND et.company = %(company)s" if company else ""
		)

		params = {
			"month_start": month_start,
			"month_end": month_end,
			"company": company,
			"employee": employee
		}
	
		results = frappe.db.sql(query, params, as_dict=True)

		for row in results:
			from_date = row.date_from
			to_date = row.date_to

			# Format months to short names and extract year
			from_str = f"{calendar.month_abbr[from_date.month]} {from_date.year}"
			to_str = f"{calendar.month_abbr[to_date.month]} {to_date.year}"

			data.append({
				"year": from_date.year,
				"from_date": from_str,
				"to_date": to_str,
				"basic_salary": row.basic_salary,
				"rate": f"{row.rate}%",
				"amount": row.amount
			})

	# Sort the data by year and month order
	data.sort(key=lambda x: (x["year"], list(calendar.month_abbr).index(x["from_date"].split(" ")[0])))

	return data



def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months