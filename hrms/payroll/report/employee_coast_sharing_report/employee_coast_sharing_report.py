# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict


def execute(filters=None):
	columns = get_columns()
	employee_rows = get_data(filters)

	#Fetch company data for header
	company_filter = filters.get("company") if filters else None
	company = frappe.get_doc("Company",company_filter) if company_filter else None

	company_data = {
		"company_name" : company.company_name if company else "",
		"organization_tin_number":company.tax_id if company else "",
		"tax_account_number":company.tax_account_number if company else "",
		"region":company.region if company else "",
		"zonesub_district":company.zonesub_district if company else "",
		"name_of_the_tax_collector":company.name_of_the_tax_collector if company else "",
		"document_number_for_office_use":company.document_number_for_office_use_only if company else "",
		"woreda":company.woreda if company else "",
		"kebele":company.kebele if company else "",
		"house_number":company.house_number if company else "",
		"phone":company.phone_no if company else "",
		"fax":company.fax if company else ""
	}
	
	if filters.get("from_date"):
		from_date = getdate(filters["from_date"])
		period_for_payment = f"{from_date.strftime('%B')} {from_date.year}"  # Format: "Month Year"
		company_data["period_for_payment"] = period_for_payment
		
	for row in employee_rows:
		row.update(company_data)
	# frappe.msgprint(f"this is the data of {data}")

	return columns, employee_rows


def get_columns():
	return[
		{"label":"የሠራተኛው ስም ፥ የአባት ስም እና የአያት ስም","fieldname":"employee_name","fieldtype":"Data","width": 200},
		{"label":"የሠራተኛው የግብር ከፋይ መለያ ቁጥር(TIN)","fieldname":"tin_number","fieldtype":"Data","width": 120},
		{"label":"የተቀጠሩበት ቀን(G.C)","fieldname":"date_of_hire","fieldtype":"Date","width":120},
		{"label":"ደመወዝ(ብር)","fieldname":"basic_salary","fieldtype":"Currency","width": 120},
		{"label":"ጠቅላላ የትራንስፖርት አበል(ብር)","fieldname":"transport_salary","fieldtype":"Currency","width":120},
		{"label":"ጠቅላላ ግብር የሚከፈልበት ገቢ/ብር/ (ሠ-ሰ-ሽ-ቀ)","fieldname":"total_tax","fieldtype":"Currency","width":120},
		{"label":"የስራ ግብር","fieldname":"employment_tax","fieldtype":"Currency","width":120},
		{"label":"የሰራተኛ ጡረታ መዋጮ","fieldname":"employee_pension","fieldtype":"Currency","width": 120},
		{"label":"የትምህርት የወጪ መጋራት ክፍያ","fieldname":"coast_sharing","fieldtype":"Currency","width": 120},
	    {"label":"የተጣራ ክፍያ","fieldname":"net_pay","fieldtype":"Currency","width": 120},
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
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    data = []
    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    # Keep latest slip per employee per month
    latest_slips = {}

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)
        month_key = month.strftime("%Y-%m")  # example: '2025-05'

        query = """
            SELECT ss.name, ss.employee, ss.end_date, ss.net_pay, ss.payment_type,
                   e.name AS employee, e.employee_name, e.department, e.designation, e.branch,
                   e.grade, e.bank_name, e.employment_type, e.employee_tin_no, e.date_of_joining, 
                   e.tax_free_transportation_amount,
                   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
                  AND ss.docstatus = 1
                  {company_clause}
                  {employee_clause}
                  {payment_type_clause}
                  {branch_clause}
                  {department_clause}
                  {grade_clause}
                  {job_title_clause}
                  {employee_type_clause}
            ORDER BY ss.end_date DESC
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
            department_clause="AND e.department = %(department)s" if department else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
            job_title_clause="AND e.designation = %(job_title)s" if job_title else "",
            employee_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else ""
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company": company,
            "employee": employee,
            "payment_type": payment_type,
            "branch": branch,
            "department": department,
            "grade": grade,
            "job_title": job_title,
            "employee_type": employee_type
        }

        results = frappe.db.sql(query, params, as_dict=True)

        # For each slip, retain highest priority per employee per month
        for row in results:
            emp = row.employee
            month_emp_key = (month_key, emp)
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1

            if month_emp_key not in latest_slips or current_index > payment_order.index(latest_slips[month_emp_key].payment_type):
                latest_slips[month_emp_key] = row

    for (month_key, emp), slip in latest_slips.items():
        salary_details = frappe.db.sql("""
            SELECT sd.amount, sd.abbr, sd.parentfield
            FROM `tabSalary Detail` sd
            WHERE sd.parent = %s
        """, (slip.name,), as_dict=True)

        earnings = {}
        deductions = {}
        for comp in salary_details:
            if comp.parentfield == 'earnings':
                earnings[comp.abbr] = comp.amount
            elif comp.parentfield == 'deductions':
                deductions[comp.abbr] = comp.amount

        # Only include if coast sharing is present
        if not deductions.get('csl'):
            continue

        basic_salary = earnings.get('B') or earnings.get('VB') or 0
        transport_salary = earnings.get('TA', 0)
        employment_tax = deductions.get('IT', 0)
        employee_pension = deductions.get('PS', 0)
        coast_sharing = deductions.get('csl', 0)

        data.append({
            "employee_name": slip.employee_name,
            "tin_number": slip.employee_tin_no,
            "date_of_hire": slip.date_of_joining,
            "basic_salary": basic_salary,
            "transport_salary": transport_salary,
            "total_tax": employment_tax,
            "employment_tax": employment_tax,
            "employee_pension": employee_pension,
            "coast_sharing": coast_sharing,
            "net_pay": slip.net_pay,
        })

    return data

def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date

    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)

    return months
   