# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Date of Hire", "fieldname": "date_of_hire", "fieldtype": "Date", "width": 120},
        {"label": "Date of Leave", "fieldname": "date_of_leave", "fieldtype": "Date", "width": 120},
        {"label": "Base Salary", "fieldname": "base", "fieldtype": "Currency", "width": 120},

        {"label": "Severance", "fieldname": "severance_gross", "fieldtype": "Currency", "width": 120},
        {"label": "Annual Leave", "fieldname": "annual_leave_gross", "fieldtype": "Currency", "width": 120},
        {"label": "Total Benefit", "fieldname": "total_benefit", "fieldtype": "Currency", "width": 120},

        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 120},
        {"label": "Total Tax", "fieldname": "total_tax", "fieldtype": "Currency", "width": 120},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters=None):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    company = filters.get("company")
    employee = filters.get("employee")
    payment_type = filters.get("payment_type")

    months = get_months_in_range(from_date, to_date)
    data = []

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        # --------------------------------------------------
        # Fetch Salary Slips for the Month
        # --------------------------------------------------
        query = """
            SELECT ss.name, ss.employee, ss.net_pay
            FROM `tabSalary Slip` ss
            WHERE ss.start_date <= %(month_end)s
              AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
              {company_clause}
              {employee_clause}
              {payment_type_clause}
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
        )

        params = {"month_start": month_start, "month_end": month_end}
        if company: params["company"] = company
        if employee: params["employee"] = employee
        if payment_type: params["payment_type"] = payment_type

        slips = frappe.db.sql(query, params, as_dict=True)

        # Group by employee
        slips_by_employee = {}
        for s in slips:
            slips_by_employee.setdefault(s.employee, []).append(s)

        # --------------------------------------------------
        # PROCESS EMPLOYEE
        # --------------------------------------------------
        for emp_id, emp_slips in slips_by_employee.items():

            latest_slip = emp_slips[-1]
            total_net_pay = sum(s.net_pay for s in emp_slips)

            # =============== EMPLOYEE INFO (FETCH DIRECTLY FROM DOCTYPE) ===============
            emp = frappe.get_doc("Employee", emp_id)

            # --------------------------------------------------
            # NEW: FILTER ONLY EMPLOYEES WHO ARE RELIEVING
            # --------------------------------------------------
            if not emp.relieving_date:
                continue

            if not (from_date <= emp.relieving_date <= to_date):
                continue

            employee_name = emp.employee_name
            department = emp.department
            date_of_hire = emp.date_of_joining
            date_of_leave = emp.relieving_date
            base_salary = emp.base or 0

            # =============== COMPONENTS ===============
            comp_details = frappe.db.sql("""
                SELECT amount, abbr, parentfield
                FROM `tabSalary Detail`
                WHERE parent=%s
            """, latest_slip.name, as_dict=True)

            earnings = {}
            deductions = {}

            for c in comp_details:
                if c.parentfield == "earnings":
                    earnings[c.abbr] = c.amount
                else:
                    deductions[c.abbr] = c.amount

            # Earnings
            severance_gross = earnings.get("sevr", 0)
            annual_leave_gross = earnings.get("annlev", 0)

            total_benefit = sum(
                val for abbr, val in earnings.items()
                if abbr not in ["B", "VB", "sevr", "annlev"]
            )

            # ----------------------------------------------
            # FIXED: REAL DEDUCTIONS (exclude taxes)
            # ----------------------------------------------
            employ_tax = deductions.get("IT", 0)
            sever_tax = deductions.get("Sevrinc", 0)
            annual_tax = deductions.get("annlevtax", 0)

            total_tax = employ_tax + sever_tax + annual_tax

            # Only deduction items EXCEPT TAXES
            real_deductions = {
                abbr: val
                for abbr, val in deductions.items()
                if abbr not in ["IT", "Sevrinc", "annlevtax"]
            }

            total_deduction = sum(real_deductions.values())

            # =============== Final Row ===============
            data.append({
                "employee_name": employee_name,
                "department": department,
                "date_of_hire": date_of_hire,
                "date_of_leave": date_of_leave,
                "base": base_salary,

                "severance_gross": severance_gross,
                "annual_leave_gross": annual_leave_gross,
                "total_benefit": total_benefit,

                "total_deduction": total_deduction,
                "total_tax": total_tax,
                "net_pay": total_net_pay,
            })

    return data


def get_months_in_range(start_date, end_date):
    months = []
    current = start_date

    while current <= end_date:
        months.append(current)
        current = add_months(current, 1)

    return months
