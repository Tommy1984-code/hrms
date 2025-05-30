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
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{"label": "Employee ID", "fieldname": "employee", "fieldtype": "Data", "width": 120},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 120},
        {"label": "Job Title", "fieldname": "job_title", "fieldtype": "Data", "width": 120},
        {"label": "Tele", "fieldname": "tele", "fieldtype": "Data", "width": 100},
        {"label": "Payment Mode", "fieldname": "payment_mode", "fieldtype": "Data", "width": 100},
        {"label": "Employment Type", "fieldname": "employment_type", "fieldtype": "Data", "width": 120},
        {"label": "Date of Hire", "fieldname": "date_of_hire", "fieldtype": "Date", "width": 100},
        {"label": "Gender", "fieldname": "gender", "fieldtype": "Data", "width": 80},
        {"label": "Tin No.", "fieldname": "tin_no", "fieldtype": "Data", "width": 120},
        {"label": "Pension ID", "fieldname": "pension_id", "fieldtype": "Data", "width": 120},
        {"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 120},
        {"label": "Basic Pay", "fieldname": "basic_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Overtime", "fieldname": "overtime", "fieldtype": "Currency", "width": 120},
        {"label": "Absence", "fieldname": "absence", "fieldtype": "Currency", "width": 100},
        {"label": "Allowance", "fieldname": "allowance", "fieldtype": "Currency", "width": 120},
        {"label": "Net Benefit Gross Up", "fieldname": "net_benefit_gross_up", "fieldtype": "Currency", "width": 150},
        {"label": "Attendance Incentive", "fieldname": "attendance_incentive", "fieldtype": "Currency", "width": 150},
        {"label": "Commission/Incentive", "fieldname": "commission_incentive", "fieldtype": "Currency", "width": 150},
        {"label": "Transport Allowance", "fieldname": "transport_allowance", "fieldtype": "Currency", "width": 150},
        {"label": "Representative Allowance", "fieldname": "representative_allowance", "fieldtype": "Currency", "width": 160},
        {"label": "Medical", "fieldname": "medical", "fieldtype": "Currency", "width": 100},
        {"label": "Insurance", "fieldname": "insurance", "fieldtype": "Currency", "width": 100},
        {"label": "Bonus", "fieldname": "bonus", "fieldtype": "Currency", "width": 100},
        {"label": "Puagume Salary (5 Days)", "fieldname": "puagume_salary", "fieldtype": "Currency", "width": 160},
        {"label": "Cash Indemnity Allowance", "fieldname": "cash_indemnity_allowance", "fieldtype": "Currency", "width": 160},
        {"label": "Housing Allowance", "fieldname": "housing_allowance", "fieldtype": "Currency", "width": 150},
        {"label": "Acting Allowance", "fieldname": "acting_allowance", "fieldtype": "Currency", "width": 130},
        {"label": "Responsibility Allowance", "fieldname": "responsibility_allowance", "fieldtype": "Currency", "width": 160},
        {"label": "Skill Allowance", "fieldname": "skill_allowance", "fieldtype": "Currency", "width": 130},
        {"label": "Total Benefit", "fieldname": "total_benefit", "fieldtype": "Currency", "width": 130},
        {"label": "Taxable Gross Pay", "fieldname": "taxable_gross", "fieldtype": "Currency", "width": 140},
        {"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Company Pension Cont.", "fieldname": "company_pension", "fieldtype": "Currency", "width": 150},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency", "width": 120},
        {"label": "Employee Pension", "fieldname": "employee_pension", "fieldtype": "Currency", "width": 150},
        {"label": "Salary Advance", "fieldname": "salary_advance", "fieldtype": "Currency", "width": 130},
        {"label": "Loan", "fieldname": "loan", "fieldtype": "Currency", "width": 100},
        {"label": "Penalty", "fieldname": "penalty", "fieldtype": "Currency", "width": 100},
        {"label": "Union", "fieldname": "union", "fieldtype": "Currency", "width": 100},
        {"label": "Cost Sharing", "fieldname": "cost_sharing", "fieldtype": "Currency", "width": 120},
        {"label": "Court", "fieldname": "court", "fieldtype": "Currency", "width": 100},
        {"label": "Bank", "fieldname": "bank", "fieldtype": "Currency", "width": 100},
        {"label": "Credit Purchase", "fieldname": "credit_purchase", "fieldtype": "Currency", "width": 130},
        {"label": "Saving", "fieldname": "saving", "fieldtype": "Currency", "width": 100},
        {"label": "Penalty 2", "fieldname": "penalty_2", "fieldtype": "Currency", "width": 100},
        {"label": "Medical 2", "fieldname": "medical_2", "fieldtype": "Currency", "width": 100},
        {"label": "Cash Indemnity 2", "fieldname": "cash_indemnity_2", "fieldtype": "Currency", "width": 140},
        {"label": "Medical Loan 1", "fieldname": "medical_loan_1", "fieldtype": "Currency", "width": 140},
        {"label": "Credit Association", "fieldname": "credit_association", "fieldtype": "Currency", "width": 140},
        {"label": "Refund", "fieldname": "refund", "fieldtype": "Currency", "width": 100},
        {"label": "Social Health Insurance", "fieldname": "social_health_insurance", "fieldtype": "Currency", "width": 160},
        {"label": "Gym", "fieldname": "gym", "fieldtype": "Currency", "width": 100},
        {"label": "Milk Sales", "fieldname": "milk_sales", "fieldtype": "Currency", "width": 120},
        {"label": "Red Cross", "fieldname": "red_cross", "fieldtype": "Currency", "width": 120},
        {"label": "Credit Association Loan", "fieldname": "credit_association_loan", "fieldtype": "Currency", "width": 160},
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 140},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 130},
    ]

def get_data(filters):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    employee = filters.get("employee")
    company = filters.get("company")
    payment_type = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")

    months = get_months_in_range(from_date, to_date)
    data = []
    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    seen_departments = set()

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)
        month_label = month.strftime('%B %Y')

        query = """
            SELECT
                e.name AS employee, e.employee_name, e.department, e.branch, e.designation, e.cell_number,
                e.employment_type, e.date_of_joining, e.gender, e.employee_tin_no, e.salary_mode, e.pension_id,
                ss.name AS salary_slip, ss.start_date, ss.end_date, ss.gross_pay, ss.net_pay, ss.total_deduction,
                ss.payment_type, sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s
              AND ss.end_date >= %(month_start)s
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
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            branch_clause = "AND e.branch = %(branch)s" if branch else "",
            department_clause = "AND e.department = %(department)s" if department else "",
            grade_clause = "AND e.grade = %(grade)s" if grade else "",
            job_title_clause = "AND e.designation = %(job_title)s" if job_title else "",
            employee_type_clause = "AND e.employment_type = %(employee_type)s" if employee_type else "",
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company": company
        }
        # if employee:
        #     params["employee"] = employee
        # if payment_type:
        #     params["payment_type"] = payment_type

        optional_fields = [
            "employee",
            "payment_type",
            "branch",
            "department",
            "grade",
            "employee_type",
        ]

        for field in optional_fields:
            value = locals().get(field)
            if value:
                params[field] = value

        results = frappe.db.sql(query, params, as_dict=True)

        grouped = {}
        for row in results:
            dept = row.department or "No Department"
            grouped.setdefault(dept, []).append(row)

        for dept, rows in grouped.items():
            # Skip departments with all zero amounts
            if not any(r.amount for r in rows):
                continue

            # Add department header only once
            if dept not in seen_departments:
                data.append({
                    "is_group_header": 1,
                    "employee_name": f" {dept}",
                   "basic_pay": None, "overtime": None, "absence": None, "allowance": None, "net_benefit_gross_up": None,
                    "attendance_incentive": None, "commission_incentive": None, "transport_allowance": None,
                    "representative_allowance": None, "medical": None, "insurance": None, "bonus": None,
                    "puagume_salary": None, "cash_indemnity_allowance": None, "housing_allowance": None,
                    "acting_allowance": None, "responsibility_allowance": None, "skill_allowance": None,
                    "total_benefit": None, "taxable_gross": None, "gross_pay": None,
                    "company_pension": None, "income_tax": None, "employee_pension": None, "salary_advance": None,
                    "loan": None, "penalty": None, "union": None, "cost_sharing": None, "court": None, "bank": None,
                    "credit_purchase": None, "saving": None, "penalty_2": None, "medical_2": None,
                    "cash_indemnity_2": None, "medical_loan_1": None, "credit_association": None, "refund": None,
                    "social_health_insurance": None, "gym": None, "milk_sales": None, "red_cross": None,
                    "credit_association_loan": None, "total_deduction": None, "net_pay": None
                })
                seen_departments.add(dept)

            latest_slips = {}
            for row in rows:
                emp = row.employee
                current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
                if emp not in latest_slips or current_index > payment_order.index(latest_slips[emp].payment_type):
                    latest_slips[emp] = row

            for emp, base in latest_slips.items():
                slip_data = [r for r in rows if r.salary_slip == base.salary_slip]

                # Employee row with all keys, zeros allowed
                row_dict = {
                    "employee": base.employee,
                    "employee_name": base.employee_name,
                    "department": base.department,
                    "branch": base.branch,
                    "job_title": base.designation,
                    "tele": base.cell_number or "",
                    "payment_mode": base.salary_mode,
                    "employment_type": base.employment_type,
                    "date_of_hire": base.date_of_joining or "",
                    "gender": base.gender or "",
                    "employee_id": base.employee,
                    "tin_no": base.employee_tin_no or "",
                    "pension_id": base.pension_id or "",
                    "period": month_label,
                    "basic_pay": 0, "overtime": 0, "absence": 0, "allowance": 0, "net_benefit_gross_up": 0,
                    "attendance_incentive": 0, "commission_incentive": 0, "transport_allowance": 0,
                    "representative_allowance": 0, "medical": 0, "insurance": 0, "bonus": 0,
                    "puagume_salary": 0, "cash_indemnity_allowance": 0, "housing_allowance": 0,
                    "acting_allowance": 0, "responsibility_allowance": 0, "skill_allowance": 0,
                    "total_benefit": 0, "taxable_gross": 0, "gross_pay": 0,
                    "company_pension": 0, "income_tax": 0, "employee_pension": 0, "salary_advance": 0,
                    "loan": 0, "penalty": 0, "union": 0, "cost_sharing": 0, "court": 0, "bank": 0,
                    "credit_purchase": 0, "saving": 0, "penalty_2": 0, "medical_2": 0,
                    "cash_indemnity_2": 0, "medical_loan_1": 0, "credit_association": 0, "refund": 0,
                    "social_health_insurance": 0, "gym": 0, "milk_sales": 0, "red_cross": 0,
                    "credit_association_loan": 0, "total_deduction": 0, "net_pay": 0
                }

                earnings_map = {
                    'B': "basic_pay", 'VB': "basic_pay", 'OT': "overtime", 'ABS': "absence",
                    'ALL': "allowance", 'NBG': "net_benefit_gross_up", 'AIN': "attendance_incentive",
                    'CIN': "commission_incentive", 'TA': "transport_allowance", 'RA': "representative_allowance",
                    'MD': "medical", 'INS': "insurance", 'Bns': "bonus", 'PUG': "puagume_salary",
                    'CIA': "cash_indemnity_allowance", 'HA': "housing_allowance", 'AA': "acting_allowance",
                    'RS': "responsibility_allowance", 'SA': "skill_allowance"
                }

                deductions_map = {
                    'IT': "income_tax", 'PS': "employee_pension", 'APNI': "salary_advance",
                    'HL': "loan", 'csl': "loan", 'PNLTY': "penalty", 'UNI': "union", 'CS': "cost_sharing",
                    'CRT': "court", 'BNK': "bank", 'CP': "credit_purchase", 'SVG': "saving",
                    'PNLTY2': "penalty_2", 'MD2': "medical_2", 'CIA2': "cash_indemnity_2",
                    'MDL1': "medical_loan_1", 'CA': "credit_association", 'RFND': "refund",
                    'SHI': "social_health_insurance", 'GM': "gym", 'MS': "milk_sales", 'RC': "red_cross",
                    'CAL': "credit_association_loan"
                }

                for r in slip_data:
                    amt = r.amount or 0
                    comp = r.abbr or r.salary_component
                    if r.parentfield == "earnings" and comp in earnings_map:
                        row_dict[earnings_map[comp]] += amt
                    elif r.parentfield == "deductions" and comp in deductions_map:
                        row_dict[deductions_map[comp]] += amt

                row_dict["gross_pay"] = base.gross_pay or 0
                row_dict["total_deduction"] = base.total_deduction or 0
                row_dict["net_pay"] = base.net_pay or 0
                row_dict["company_pension"] = row_dict["basic_pay"] * 0.11

                data.append(row_dict)

    return data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months