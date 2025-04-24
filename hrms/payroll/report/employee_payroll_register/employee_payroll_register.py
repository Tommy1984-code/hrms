# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict


def execute(filters=None):
	columns= get_columns()
	data = get_data(filters)
     
	return columns ,data


def get_columns():
    return [
        {"label": "Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Basic Pay", "fieldname": "basic", "fieldtype": "Currency", "width": 100},
        {"label": "Absence", "fieldname": "absence", "fieldtype": "Currency", "width": 100},
        {"label": "Hardship Allowance", "fieldname": "hardship", "fieldtype": "Currency", "width": 120},
        {"label": "Overtime", "fieldname": "overtime", "fieldtype": "Currency", "width": 100},
        {"label": "Commission", "fieldname": "commission", "fieldtype": "Currency", "width": 100},
        {"label": "Incentive", "fieldname": "incentive", "fieldtype": "Currency", "width": 100},
        {"label": "Taxable Gross Pay", "fieldname": "taxable_gross", "fieldtype": "Currency", "width": 120},
        {"label": "Gross Pay", "fieldname": "gross", "fieldtype": "Currency", "width": 100},
        {"label": "Company Pension", "fieldname": "company_pension", "fieldtype": "Currency", "width": 120},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency", "width": 100},
        {"label": "Employee Pension", "fieldname": "employee_pension", "fieldtype": "Currency", "width": 100},
        {"label": "Other Deduction", "fieldname": "other_deduction", "fieldtype": "Currency", "width": 100},
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 100},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 100},
        {"label": "Signature", "fieldname": "signature", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters=None):
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	company = filters.get("company")

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	months = get_months_in_range(from_date, to_date)
	data = []

	payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

	for month in months:
		month_start = month.replace(day=1)
		month_end = add_months(month_start, 1) - timedelta(days=1)

		query = """
			SELECT
				e.name AS employee,
				e.employee_name,
				e.department,
				ss.name AS salary_slip,
				ss.gross_pay,
				ss.net_pay,
				ss.total_deduction,
				ss.payment_type,
				sd.salary_component,
				sd.abbr,
				sd.amount,
				sd.parentfield
			FROM `tabSalary Slip` ss
			JOIN `tabEmployee` e ON ss.employee = e.name
			JOIN `tabSalary Detail` sd ON sd.parent = ss.name
			WHERE ss.start_date <= %(month_end)s
			  AND ss.end_date >= %(month_start)s
			  AND ss.docstatus = 1
			  {company_clause}
			ORDER BY ss.end_date DESC
		""".format(company_clause="AND ss.company = %(company)s" if company else "")

		results = frappe.db.sql(query, {
			"month_start": month_start,
			"month_end": month_end,
			"company": company
		}, as_dict=True)

		# Get latest slip per employee by payment type order
		latest_slips = {}
		for row in results:
			emp = row.employee
			current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1

			if emp not in latest_slips:
				latest_slips[emp] = []
			latest_slips[emp].append(row)

		final_slips = {}
		for emp, rows in latest_slips.items():
			highest = None
			for row in rows:
				current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
				if not highest or current_index > payment_order.index(highest.payment_type):
					highest = row
			final_slips[emp] = highest

		grouped_data = {}
		for row in results:
			if final_slips.get(row.employee) and row.salary_slip != final_slips[row.employee].salary_slip:
				continue

			if row.employee not in grouped_data:
				grouped_data[row.employee] = {
					"employee_name": row.employee_name,
					"department": row.department,
					"gross_pay": row.gross_pay,
					"net_pay": row.net_pay,
					"total_deduction": row.total_deduction,
					"basic": 0,
					"hardship": 0,
					"overtime": 0,
					"commission": 0,
					"incentive": 0,
					"income_tax": 0,
					"employee_pension": 0,
					"absence": 0,
					"other_deduction": 0
				}

			comp = row.abbr or row.salary_component
			val = row.amount or 0
			field = row.parentfield

			if field == "earnings":
				if comp in ('B', 'VB'):
					grouped_data[row.employee]["basic"] += val
				elif comp == 'HDA':
					grouped_data[row.employee]["hardship"] += val
				elif comp == 'OT':
					grouped_data[row.employee]["overtime"] += val
				elif comp == 'C':
					grouped_data[row.employee]["commission"] += val
				elif comp == 'PP':
					grouped_data[row.employee]["incentive"] += val

			elif field == "deductions":
				if comp == 'IT':
					grouped_data[row.employee]["income_tax"] += val
				elif comp == 'PS':
					grouped_data[row.employee]["employee_pension"] += val
				elif comp == 'ABT':
					grouped_data[row.employee]["absence"] += val
				else:
					grouped_data[row.employee]["other_deduction"] += val

		# Group by department
		dept_group = {}
		for emp, g in grouped_data.items():
			dept = g.get("department") or "No Department"
			if dept not in dept_group:
				dept_group[dept] = []
			g["company_pension"] = g["basic"] * 0.11
			g["taxable_gross"] = g["basic"] + g["hardship"] + g["overtime"] + g["commission"] + g["incentive"]
			dept_group[dept].append(g)

		for dept, employees in dept_group.items():
			# Add department title row
			num_columns = len(get_columns())
			data.append([f"▶ {dept}"] + [None] * (num_columns - 1))


			for g in employees:
				row = [
					g["employee_name"],
					*(val if val else "" for val in [
						g["basic"], g["absence"], g["hardship"], g["overtime"], g["commission"],
						g["incentive"], g["taxable_gross"], g["gross_pay"], g["company_pension"],
						g["income_tax"], g["employee_pension"], g["other_deduction"],
						g["total_deduction"], g["net_pay"]
					]),
					""  # Signature column
				]
				data.append(row)

	return data

def get_months_in_range(start_date, end_date):
	months = []
	current_month = start_date.replace(day=1)

	while current_month <= end_date:
		months.append(current_month)
		current_month = add_months(current_month, 1)

	return months