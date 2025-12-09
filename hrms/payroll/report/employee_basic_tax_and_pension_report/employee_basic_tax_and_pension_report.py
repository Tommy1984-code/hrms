# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
     
	employee_filter = filters.get("employee") if filters else None
	employee = frappe.get_doc("Employee",employee_filter) if employee_filter else None
	employee_data = {
		"employee_tin" : employee.employee_tin_no if employee_filter else None,
        "employee_name" : employee.employee_name if employee_filter else None 
	}
     
	company_filter = filters.get("company") if filters else None
	company = frappe.get_doc("Company",company_filter) if company_filter else None
	company_data= {
		"company_tin" : company.tax_id if company else ""
	}
	for row in data:
		row.update(employee_data)
		row.update(company_data)
    
	return columns,data


def get_columns():
    return [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": "Basic Salary", "fieldname": "basic_salary", "fieldtype": "Currency", "width": 120},
        {"label": "Other Taxable Income", "fieldname": "other_income", "fieldtype": "Currency", "width": 160},
        {"label": "Cost Sharing", "fieldname": "cost_sharing", "fieldtype": "Currency", "width": 120},
        {"label": "Tax on Gross Monthly Income", "fieldname": "tax", "fieldtype": "Currency", "width": 180},
        {"label": "Pension", "fieldname": "pension", "fieldtype": "Currency", "width": 100},
    ]

def get_data(filters=None):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    employee = filters.get("employee")
    payment_type = filters.get("payment_type")
    
    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    data = []
    payment_order = ["First Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
            SELECT ss.name, ss.employee, ss.end_date, ss.payment_type,
                   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
                  AND ss.docstatus = 1
                  {company_clause}
                  {employee_clause}
                  {payment_type_clause}
                 
            ORDER BY ss.end_date DESC
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company": company,
            "employee": employee,
            "payment_type": payment_type,
        }

        results = frappe.db.sql(query, params, as_dict=True)

        # Group by salary slip and select latest slip per employee by payment type
        slip_map = {}
        for row in results:
            emp = row.employee
            slip_key = (emp, row["name"])
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1

            if slip_key not in slip_map or current_index > payment_order.index(slip_map[slip_key]["payment_type"]):
                slip_map[slip_key] = {
                    "name": row.name,
                    "employee": row.employee,
                    "end_date": row.end_date,
                    "payment_type": row.payment_type,
                    "components": [],
                    # ✅ Fetch taxable gross here
                    "taxable_income": frappe.db.get_value(
                        "Salary Slip", row.name, "taxable_gross_pay"
                    ) or 0
                }

            slip_map[slip_key]["components"].append(row)

        for slip in slip_map.values():
            earnings = {}
            deductions = {}

            for comp in slip["components"]:
                if comp.parentfield == "earnings":
                    earnings[comp.abbr] = comp.amount
                elif comp.parentfield == "deductions":
                    deductions[comp.abbr] = comp.amount

            basic_salary = earnings.get("B") or earnings.get("VB") or 0
            pension = deductions.get("PS", 0)
            cost_sharing = deductions.get("csl", 0)
            tax = deductions.get("IT", 0)

            # Replace old logic → new required logic:
            taxable_income = slip.get("taxable_income", 0)
            other_income = max(taxable_income - basic_salary, 0)

            # --- Handle and format the payment month ---
            end_date = slip["end_date"] 
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            formatted_month = end_date.strftime("%B %Y") 
            
            data.append({
                "month": formatted_month,
                "basic_salary": basic_salary,
                "other_income": other_income,
                "cost_sharing": cost_sharing,
                "tax": tax,
                "pension": pension
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
