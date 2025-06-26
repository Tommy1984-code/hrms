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
    fixed_columns = [
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
    ]

    earnings, deductions = get_dynamic_salary_components()

    total_columns = [
        {"label": "Total Benefit", "fieldname": "total_benefit", "fieldtype": "Currency", "width": 130},
        {"label": "Taxable Gross Pay", "fieldname": "taxable_gross", "fieldtype": "Currency", "width": 140},
        {"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Company Pension Cont.", "fieldname": "company_pension", "fieldtype": "Currency", "width": 150},
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 140},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 130},
    ]

    return fixed_columns + earnings + deductions + total_columns


def get_dynamic_salary_components():
    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["name", "salary_component_abbr", "type"]
    )
    seen = set()
    earnings = []
    deductions = []
    basic_salary_added = False

    for comp in components:
        abbr = comp.salary_component_abbr
        if abbr in seen:
            continue
        seen.add(abbr)
        # Skip company pension if it's a defined component — we calculate it manually
        if frappe.scrub(abbr) == "CP":
            continue

        if abbr in ("B", "VB"):
            if not basic_salary_added:
                column = {
                    "label": "Basic Salary",
                    "fieldname": "basic_pay",
                    "fieldtype": "Currency",
                    "width": 140
                }
                earnings.insert(0, column)  # Ensure it's first
                basic_salary_added = True
            continue

        column = {
            "label": comp.name,
            "fieldname": frappe.scrub(abbr),
            "fieldtype": "Currency",
            "width": 140
        }
        if comp.type == "Earning":
            earnings.append(column)
        elif comp.type == "Deduction":
            deductions.append(column)

    return earnings, deductions


def get_active_component_map():
    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["salary_component_abbr", "type"]
    )
    earning_abbrs = {}
    deduction_abbrs = {}
    for c in components:
        fieldname = "basic_pay" if c.salary_component_abbr in ("B", "VB") else frappe.scrub(c.salary_component_abbr)
        if c.type == "Earning":
            earning_abbrs[c.salary_component_abbr] = fieldname
        elif c.type == "Deduction":
            deduction_abbrs[c.salary_component_abbr] = fieldname
    return earning_abbrs, deduction_abbrs


def aggregate_salary_components(rows):
    result = defaultdict(float)
    earnings_map, deductions_map = get_active_component_map()

    gross_pays = set()
    net_pays = set()
    total_deductions = set()

    for r in rows:
        amt = r.amount or 0
        abbr = r.abbr or r.salary_component
        fieldname = None

        if abbr in ("B", "VB"):
            fieldname = "basic_pay"
        elif r.parentfield == "earnings" and abbr in earnings_map:
            fieldname = earnings_map[abbr]
        elif r.parentfield == "deductions" and abbr in deductions_map:
            fieldname = deductions_map[abbr]

        if fieldname:
            result[fieldname] += amt

        gross_pays.add((r.salary_slip, r.gross_pay or 0))
        net_pays.add((r.salary_slip, r.net_pay or 0))
        total_deductions.add((r.salary_slip, r.total_deduction or 0))

    result["gross_pay"] = sum(v for _, v in gross_pays)
    result["net_pay"] = sum(v for _, v in net_pays)
    result["total_deduction"] = sum(v for _, v in total_deductions)

    # Only add company_pension if it's not already defined
    if "company_pension" not in result:
        result["company_pension"] = result.get("basic_pay", 0) * 0.11

    return result

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
        "company": company
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

    data_by_employee_slip = defaultdict(lambda: defaultdict(list))
    for r in results:
        emp = r.employee
        slip = r.salary_slip
        data_by_employee_slip[emp][slip].append(r)

    grouped_data = defaultdict(list)

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

    final_data = []

    earnings, deductions = get_dynamic_salary_components()
    component_fieldnames = [c["fieldname"] for c in earnings + deductions]

    total_fields = [
        "gross_pay", "net_pay", "total_deduction",
        "company_pension", "total_benefit", "taxable_gross"
    ]
    
    for dept in sorted(grouped_data.keys()):
        dept_row = {"employee_name": f"{dept}"}
        for field in component_fieldnames + total_fields:
            dept_row[field] = None

        final_data.append(dept_row)
        final_data.extend(grouped_data[dept])

    return final_data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months