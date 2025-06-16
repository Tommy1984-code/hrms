# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta
from collections import defaultdict



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
    company = filters.get("company")
    employee = filters.get("employee")
    payment_type_filter = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")

    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    query = f"""
        SELECT
            e.name AS employee, e.employee_name, e.department, e.branch, e.designation, e.cell_number,
            e.employment_type, e.date_of_joining, e.gender, e.employee_tin_no, e.salary_mode, e.pension_id,
            ss.name AS salary_slip, ss.start_date, ss.end_date, ss.gross_pay, ss.net_pay, ss.total_deduction,
            ss.payment_type, sd.salary_component, sd.abbr, sd.amount, sd.parentfield
        FROM `tabSalary Slip` ss
        JOIN `tabEmployee` e ON ss.employee = e.name
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE ss.start_date >= %(from_date)s
          AND ss.end_date <= %(to_date)s
          AND ss.docstatus = 1
          {"AND ss.company = %(company)s" if company else ""}
          {"AND ss.employee = %(employee)s" if employee else ""}
          {"AND ss.payment_type = %(payment_type)s" if payment_type_filter else ""}
          {"AND e.branch = %(branch)s" if branch else ""}
          {"AND e.department = %(department)s" if department else ""}
          {"AND e.grade = %(grade)s" if grade else ""}
          {"AND e.designation = %(job_title)s" if job_title else ""}
          {"AND e.employment_type = %(employee_type)s" if employee_type else ""}
    """

    params = {
        "from_date": from_date,
        "to_date": to_date,
        "company":company
    }
    if employee:
        params["employee"] = employee
    if payment_type_filter:
        params["payment_type"] = payment_type_filter
    if branch:
        params["branch"] = branch
    if department:
        params["department"] = department
    if grade:
        params["grade"] = grade
    if job_title:
        params["job_title"] = job_title
    if employee_type:
        params["employee_type"] = employee_type

    results = frappe.db.sql(query, params, as_dict=True)

    # Group salary details by employee and salary slip
    data_by_employee_slip = defaultdict(lambda: defaultdict(list))
    for r in results:
        emp = r.employee
        slip = r.salary_slip
        data_by_employee_slip[emp][slip].append(r)

    grouped_data = defaultdict(list)  # key = department

    def process_employee(emp, slips):
        if payment_type_filter:
            all_rows = [row for slip_rows in slips.values() for row in slip_rows]
        else:
            slips_by_month = defaultdict(list)
            for slip_rows in slips.values():
                month_key = slip_rows[0].start_date.strftime("%Y-%m")
                slips_by_month[month_key].append(slip_rows)

            all_rows = []
            for slips_list in slips_by_month.values():
                best_slip = None
                best_priority = -1
                latest_date = None
                for slip_rows in slips_list:
                    pt = slip_rows[0].payment_type
                    prio = payment_order.index(pt) if pt in payment_order else -1
                    slip_end_date = slip_rows[0].end_date or slip_rows[0].start_date
                    if prio > best_priority or (prio == best_priority and slip_end_date > latest_date):
                        best_priority = prio
                        latest_date = slip_end_date
                        best_slip = slip_rows
                if best_slip:
                    all_rows.extend(best_slip)

        if all_rows:
            aggregated = aggregate_salary_components(all_rows)
            base = all_rows[0]
            dept = base.department or "Other"

            aggregated.update({
                "employee": emp,
                "employee_name": base.employee_name,
                "department": dept,
                "branch": base.branch,
                "job_title": base.designation,
                "tele": base.cell_number or "",
                "payment_mode": base.salary_mode,
                "employment_type": base.employment_type,
                "date_of_hire": base.date_of_joining or "",
                "gender": base.gender or "",
                "employee_id": emp,
                "tin_no": base.employee_tin_no or "",
                "pension_id": base.pension_id or "",
                "period": f"{from_date.strftime('%d %b %Y')} - {to_date.strftime('%d %b %Y')}",
            })

            grouped_data[dept].append(aggregated)

    for emp, slips in data_by_employee_slip.items():
        process_employee(emp, slips)

    # Build final data list with department headers
    final_data = []
    for dept in sorted(grouped_data.keys()):
        final_data.append({
            "employee_name": f"▶{dept}",
            "basic_pay":None,"overtime":None,"absence":None,"allowance":None,"net_benefit_gross_up":None,"attendance_incentive":None,
            "commission_incentive":None,"transport_allowance":None,"representative_allowance":None,"medical":None,"insurance":None,
            "bonus":None,"puagume_salary":None,"cash_indemnity_allowance":None,"housing_allowance":None,"acting_allowance":None,
            "responsibility_allowance":None,"kill_allowance":None,"income_tax":None,"employee_pension":None,"salary_advance":None,
            "absence":None,"loan":None,"penalty":None,"union":None,"cost_sharing":None,"court":None,"bank":None,"credit_purchase":None,
            "saving":None,"penalty_2":None,"medical_2":None,"cash_indemnity_2":None,"medical_loan_1":None,"credit_association":None,
            "refund":None,"social_health_insurance":None,"gym":None,"milk_sales":None,"red_cross":None,"credit_association_loan":None,
            "gross_pay":None,"net_pay":None,"total_deduction":None,"company_pension":None,"skill_allowance":None,"total_benefit":None,
            "taxable_gross":None

        })
        final_data.extend(grouped_data[dept])

    return final_data

def aggregate_salary_components(rows):
    result = defaultdict(float)

    earnings_map = {
        'B': "basic_pay", 'VB': "basic_pay", 'OT': "overtime", 'ABS': "absence",
        'ALL': "allowance", 'NBG': "net_benefit_gross_up", 'AIN': "attendance_incentive",
        'CIN': "commission_incentive", 'TA': "transport_allowance", 'RA': "representative_allowance",
        'MD': "medical", 'INS': "insurance", 'Bns': "bonus", 'PUG': "puagume_salary",
        'CIA': "cash_indemnity_allowance", 'HA': "housing_allowance", 'AA': "acting_allowance",
        'RS': "responsibility_allowance", 'SA': "skill_allowance","TB":"total_benefit"
    }

    deductions_map = {
        'IT': "income_tax", 'PS': "employee_pension", 'APNI': "salary_advance","ABT":"absence",
        'HL': "loan",'PNLTY': "penalty", 'UNI': "union", 'csl': "cost_sharing",
        'CRT': "court", 'BNK': "bank", 'CP': "credit_purchase", 'SVG': "saving",
        'PNLTY2': "penalty_2", 'MD2': "medical_2", 'CIA2': "cash_indemnity_2",
        'MDL1': "medical_loan_1", 'CA': "credit_association", 'RFND': "refund",
        'SHI': "social_health_insurance", 'GM': "gym", 'MS': "milk_sales", 'RC': "red_cross",
        'CAL': "credit_association_loan","TG":"taxable_gross"
    }

    gross_pays = set()
    net_pays = set()
    total_deductions = set()

    for r in rows:
        amt = r.amount or 0
        comp = r.abbr or r.salary_component
        if r.parentfield == "earnings" and comp in earnings_map:
            result[earnings_map[comp]] += amt
        elif r.parentfield == "deductions" and comp in deductions_map:
            result[deductions_map[comp]] += amt

        gross_pays.add((r.salary_slip, r.gross_pay or 0))
        net_pays.add((r.salary_slip, r.net_pay or 0))
        total_deductions.add((r.salary_slip, r.total_deduction or 0))

    # Take latest values only once from each slip (to avoid duplication)
    result["gross_pay"] = sum(v for k, v in gross_pays)
    result["net_pay"] = sum(v for k, v in net_pays)
    result["total_deduction"] = sum(v for k, v in total_deductions)

    result["company_pension"] = result["basic_pay"] * 0.11

    return result


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months