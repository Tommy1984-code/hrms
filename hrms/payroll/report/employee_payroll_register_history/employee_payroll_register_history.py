# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta


def execute(filters=None):
	employee_filter = filters.get("employee") if filters else None

	columns = get_columns()
	data = get_data(filters)

	employee_info = {}

	if employee_filter:
		employee = frappe.get_value(
			"Employee",
			employee_filter,
			["employee","employee_name", "department", "grade", "employment_type", "branch"],
			as_dict=True
		)

		if employee:
			employee_info = {
				"employee_name": employee.employee_name,
				"department": employee.department,
				"grade": employee.grade,
				"employee_type": employee.employment_type,
				"branch": employee.branch
			}

	# Inject employee info into each row of the report
	for row in data:
		row.update(employee_info)

	return columns, data



def get_columns():
    return [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": "Basic Pay", "fieldname": "basic", "fieldtype": "Currency", "width": 100},
        {"label": "Hardship Allowance", "fieldname": "hardship", "fieldtype": "Currency", "width": 120},
        {"label": "Commission", "fieldname": "commission", "fieldtype": "Currency", "width": 100},
        {"label": "Overtime", "fieldname": "overtime", "fieldtype": "Currency", "width": 100},
        {"label": "Duty", "fieldname": "duty", "fieldtype": "Currency", "width": 100},
        {"label": "Gross Pay", "fieldname": "gross", "fieldtype": "Currency", "width": 100},
        {"label": "Company Pension", "fieldname": "company_pension", "fieldtype": "Currency", "width": 120},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency", "width": 100},
        {"label": "Employee Pension", "fieldname": "employee_pension", "fieldtype": "Currency", "width": 100},
        {"label": "Salary Advance", "fieldname": "salary_advance", "fieldtype": "Currency", "width": 120},
        {"label": "Loan", "fieldname": "loan", "fieldtype": "Currency", "width": 120},
        {"label": "Gym", "fieldname": "gym", "fieldtype": "Currency", "width": 100},
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 100},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 100},
    ]


def get_data(filters):
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	employee = filters.get("employee")
	company = filters.get("company")
	payment_type = filters.get("payment_type")

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	months = get_months_in_range(from_date, to_date)
	data = []

	for month in months:
		month_start = month.replace(day=1)
		month_end = add_months(month_start, 1) - timedelta(days=1)
		month_label = month.strftime('%B %Y')

		query = """
			SELECT ss.name AS salary_slip, ss.employee, ss.gross_pay, ss.net_pay,
				   ss.total_deduction, ss.payment_type,
				   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
			FROM `tabSalary Slip` ss
			JOIN `tabSalary Detail` sd ON sd.parent = ss.name
			WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
			  AND ss.docstatus = 1
			  {employee_clause}
			  {company_clause}
			  {payment_type_clause}
			ORDER BY ss.end_date DESC
		""".format(
			employee_clause="AND ss.employee = %(employee)s" if employee else "",
			company_clause="AND ss.company = %(company)s" if company else "",
			payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
		)

		params = {
			"month_start": month_start,
			"month_end": month_end,
			"employee": employee,
			"company": company
		}
		if payment_type:
			params["payment_type"] = payment_type

		results = frappe.db.sql(query, params, as_dict=True)

		# Group results by salary slip name
		slip_map = {}
		for row in results:
			slip_map.setdefault(row.salary_slip, {
				"employee": row.employee,
				"gross": row.gross_pay,
				"net": row.net_pay,
				"total_deduction": row.total_deduction,
				"components": [],
				"payment_type": row.payment_type
			})["components"].append(row)

		# Process each salary slip
		for slip_id, slip_data in slip_map.items():
			row_dict = {
				"month": month_label,
				"basic": 0,
				"hardship": 0,
				"commission": 0,
				"overtime": 0,
				"duty": 0,
				"gross": slip_data["gross"],
				"company_pension": 0,
				"income_tax": 0,
				"employee_pension": 0,
				"salary_advance": 0,
				"loan": 0,
				"gym": 0,
				"total_deduction": slip_data["total_deduction"],
				"net_pay": slip_data["net"],
			}

			for r in slip_data["components"]:
				amt = r.amount or 0
				comp = r.abbr or r.salary_component

				if r.parentfield == "earnings":
					if comp in ('B', 'VB'):
						row_dict["basic"] += amt
					elif comp == 'HDA':
						row_dict["hardship"] += amt
					elif comp == 'C':
						row_dict["commission"] += amt
					elif comp == 'OT':
						row_dict["overtime"] += amt
					elif comp == 'DY':
						row_dict["duty"] += amt
				elif r.parentfield == "deductions":
					if comp == 'IT':
						row_dict["income_tax"] += amt
					elif comp == 'PS':
						row_dict["employee_pension"] += amt
					elif comp == 'APNI':
						row_dict["salary_advance"] += amt
					elif comp in ('HL', 'csl'):
						row_dict["loan"] += amt
					elif comp == 'GM':
						row_dict["gym"] += amt

			row_dict["company_pension"] = row_dict["basic"] * 0.11

			data.append(row_dict)

	return data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months