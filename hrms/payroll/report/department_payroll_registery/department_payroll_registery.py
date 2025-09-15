# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns,data


def get_columns():
    return [
        {"label": "Department", "fieldname": "department_name", "fieldtype": "Data", "width": 150},
        {"label": "Basic Pay", "fieldname": "basic", "fieldtype": "Currency", "width": 100},
        {"label": "Absence", "fieldname": "absence", "fieldtype": "Currency", "width": 100},
        {"label": "Total Benefits", "fieldname": "total_benefits", "fieldtype": "Currency", "width": 120},
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
        
    ]

def get_data(filters=None):
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	payment_type = filters.get("payment_type")
	branch = filters.get("branch")
	department = filters.get("department")

	if not (from_date and to_date):
		frappe.throw("Please set both From Date and To Date")

	months = get_months_in_range(from_date, to_date)
	payment_order = ["Advance Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
	grouped_data = {}
	processed_slips = set()
	
	for month in months:
		month_start = month.replace(day=1)
		month_end = add_months(month_start, 1) - timedelta(days=1)

		query = """
			SELECT
				e.name AS employee,
				e.employee_name,
				e.department,
				e.tax_free_transportation_amount AS tax_free_transport,
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
			JOIN `tabDepartment` d ON e.department = d.name
			WHERE ss.start_date <= %(month_end)s
			  AND ss.end_date >= %(month_start)s
			  AND ss.docstatus = 1
			  
			  {company_clause}
			  {department_clause}
			  {payment_type_clause}
			  {branch_clause}
			ORDER BY ss.end_date DESC
		""".format(
			company_clause="AND ss.company = %(company)s" if company else "",
			department_clause="AND ss.department = %(department)s" if department else "",
			payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
			branch_clause = "AND d.branch = %(branch)s" if branch else ""
		)
		
		params = {
			"month_start": month_start,
			"month_end": month_end,
			"company": company
		}
		if department:
			params["department"] = department
		if payment_type:
			params["payment_type"] = payment_type
		if branch:
			params["branch"] = branch

		results = frappe.db.sql(query, params, as_dict=True)

		# Get latest slip per employee
		latest_slips = {}
		for row in results:
			emp = row.employee
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

		for row in results:
			if final_slips.get(row.employee) and row.salary_slip != final_slips[row.employee].salary_slip:
				continue

			if row.employee not in grouped_data:
				grouped_data[row.employee] = {
					"employee_name": row.employee_name,
					"department": row.department,
					"gross": 0, "net_pay": 0, "total_deduction": 0,
					"basic": 0, "total_benefits": 0, "overtime": 0, "commission": 0,
					"incentive": 0, "income_tax": 0, "employee_pension": 0,
					"absence": 0, "other_deduction": 0,
					"tax_free_transport": 0
				}

			comp = row.abbr or row.salary_component
			val = row.amount or 0
			field = row.parentfield
			
			raw = row.tax_free_transport or ""
			if raw == "2200":
				tax_free = 2200.0
			elif raw == "600":
				tax_free = 600.0
			else:
				tax_free = 0.0  # "All Tax" or empty

			grouped_data[row.employee]["tax_free_transport"] = tax_free

			if field == "earnings":
				if comp in ('B', 'VB'):
					grouped_data[row.employee]["basic"] += val
				elif comp == 'OT':
					grouped_data[row.employee]["overtime"] += val
				elif comp == 'C':
					grouped_data[row.employee]["commission"] += val
				elif comp == 'ICV':
					grouped_data[row.employee]["incentive"] += val
				else:
					grouped_data[row.employee]["total_benefits"] += val

			elif field == "deductions":
				if comp == 'IT':
					grouped_data[row.employee]["income_tax"] += val
				elif comp == 'PS':
					grouped_data[row.employee]["employee_pension"] += val
				elif comp == 'ABT':
					grouped_data[row.employee]["absence"] += val
				else:
					grouped_data[row.employee]["other_deduction"] += val

			# Sum once per salary slip
			if row.salary_slip not in processed_slips:
				grouped_data[row.employee]["gross"] += row.gross_pay or 0
				grouped_data[row.employee]["net_pay"] += row.net_pay or 0
				grouped_data[row.employee]["total_deduction"] += row.total_deduction or 0
				processed_slips.add(row.salary_slip)

	# Group by department
	dept_group = {}
	for emp, g in grouped_data.items():
		dept = g.get("department") or "No Department"
		if dept not in dept_group:
			dept_group[dept] = []

		g["company_pension"] = g["basic"] * 0.11
		g["taxable_gross"] = g["gross"] - g.get("tax_free_transport", 0)

		dept_group[dept].append(g)

	# Fetch branch info for each department
	department_branches = {}
	departments = frappe.get_all("Department", fields=["name", "branch"])
	for dept in departments:
		department_branches[dept.name] = dept.branch or "No Branch"

	# Summarize departments
	branch_group = {}
	for dept, records in dept_group.items():
		summary = {
			"department_name": dept,
			"basic": 0, "absence": 0, "total_benefits": 0, "overtime": 0,
			"commission": 0, "incentive": 0, "taxable_gross": 0,
			"gross": 0, "company_pension": 0, "income_tax": 0,
			"employee_pension": 0, "other_deduction": 0,
			"total_deduction": 0, "net_pay": 0
		}
		for r in records:
			for key in summary.keys():
				if key != "department_name":
					summary[key] += r.get(key, 0)

		branch = department_branches.get(dept, "No Branch")
		if branch not in branch_group:
			branch_group[branch] = []
		branch_group[branch].append(summary)

	# Flatten result with branch headers
	department_summary = []
	for branch, dept_summaries in sorted(branch_group.items()):
		department_summary.append({
			"department_name": f"▶ {branch}","basic": None, "absence": None, 
			"total_benefits": None, "overtime": None,
			"commission": None, "incentive": None, "taxable_gross": None,
			"gross": None, "company_pension": None, "income_tax": None,
			"employee_pension": None, "other_deduction": None,
			"total_deduction": None, "net_pay": None
		})
		department_summary.extend(dept_summaries)

	return department_summary


def get_months_in_range(start_date, end_date):
	months = []
	current_month = start_date.replace(day=1)

	while current_month <= end_date:
		months.append(current_month)
		current_month = add_months(current_month, 1)

	return months