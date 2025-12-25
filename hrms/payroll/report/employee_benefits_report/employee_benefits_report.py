# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta
from collections import defaultdict

def execute(filters=None):
    if filters is None:
        filters = {}

    selected_earnings = frappe.parse_json(filters.get("selected_earnings") or "[]")

    columns = get_columns(selected_earnings)
    data = get_data(filters, selected_earnings)
    return columns, data

def get_columns(selected_earnings=None):
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

    earnings = get_dynamic_salary_components(selected_earnings)
    
    # Add total columns at the end
    earnings.append({"label": "Total Benefit", "fieldname": "total_benefit", "fieldtype": "Float", "width": 130})
    earnings.append({"label": "Taxable Gross Pay", "fieldname": "taxable_gross", "fieldtype": "Float", "width": 140})
    earnings.append({"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Float", "width": 120})
    
    return fixed_columns + earnings

def get_dynamic_salary_components(selected_earnings=None):
    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["name", "salary_component_abbr", "type"]
    )
    seen = set()
    earnings = []

    basic_salary_column = None
    house_allowance_column = None
    overtime_column = None

    for comp in components:
        abbr = comp.salary_component_abbr
        if abbr in seen:
            continue
        seen.add(abbr)

        if frappe.scrub(abbr) in ("cp", "ta"):  # Skip company pension and normal transport
            continue

        column = {
            "label": comp.name,
            "fieldname": frappe.scrub(abbr),
            "fieldtype": "Float",
            "width": 140
        }

        if abbr in ("B", "VB"):
            basic_salary_column = {"label": "Basic Salary", "fieldname": "basic_pay", "fieldtype": "Float", "width": 140}
            continue

        if comp.type == "Earning":
            if not selected_earnings or comp.name in selected_earnings:
                if comp.name.lower() == "house allowance":
                    house_allowance_column = column
                    continue
                if comp.name.lower() == "overtime":
                    overtime_column = column
                    continue
                earnings.append(column)

    # Add special components in priority order
    ordered_earnings = []
    if basic_salary_column:
        ordered_earnings.append(basic_salary_column)
    if overtime_column:
        ordered_earnings.append(overtime_column)

    # Transport Allowance Exempt
    transport_exempt_column = {"label": "Transport Allowance Exempt", "fieldname": "transport_allowance_exempt", "fieldtype": "Float", "width": 140}
    ordered_earnings.append(transport_exempt_column)

    if house_allowance_column:
        ordered_earnings.append(house_allowance_column)

    ordered_earnings.extend(earnings)
    return ordered_earnings

def get_tax_free_transportation_map(employee_names):
    result = {}
    if not employee_names:
        return result
    employees = frappe.get_all("Employee",
        filters={"name": ["in", employee_names]},
        fields=["name", "tax_free_transportation_amount"]
    )
    for emp in employees:
        try:
            result[emp.name] = float(emp.tax_free_transportation_amount)
        except (ValueError, TypeError):
            result[emp.name] = 0
    return result

def aggregate_salary_components(rows, allowed_fields=None):
    result = defaultdict(float)
    earnings_map = {c.salary_component_abbr: frappe.scrub(c.salary_component_abbr) for c in frappe.get_all("Salary Component", filters={"statistical_component": 0, "disabled": 0}, fields=["salary_component_abbr", "type"])}

    total_benefit = 0
    gross_pays = set()
    taxable_gross_pays = set()

    for r in rows:
        amt = r.amount or 0
        abbr = r.abbr or r.salary_component
        fieldname = None

        if abbr in ("B", "VB"):
            fieldname = "basic_pay"
        elif r.parentfield == "earnings" and abbr in earnings_map:
            fieldname = earnings_map[abbr]

        if fieldname and (not allowed_fields or fieldname in allowed_fields):
            result[fieldname] += amt

        if r.parentfield == "earnings" and abbr not in ("B", "VB"):
            total_benefit += amt

        gross_pays.add((r.salary_slip, r.gross_pay or 0))
        taxable_gross_pays.add((r.salary_slip, r.taxable_gross_pay or 0))

    result["gross_pay"] = sum(v for _, v in gross_pays)
    result["taxable_gross"] = sum(v for _, v in taxable_gross_pays)
    result["total_benefit"] = total_benefit

    return result

def get_data(filters, selected_earnings=None):
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
    employee_status = filters.get("employee_status") or "All"

    payment_order = ["First Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    query = f"""
        SELECT
            e.name AS employee, e.employee_name, e.department, e.branch, e.designation, e.cell_number,
            e.employment_type, e.date_of_joining, e.gender, e.employee_tin_no, e.salary_mode, e.pension_id,
            ss.name AS salary_slip, ss.start_date, ss.end_date, ss.gross_pay, ss.taxable_gross_pay,
            sd.salary_component, sd.abbr, sd.amount, sd.parentfield
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

    if employee_status == "New Employees":
        query += " AND e.date_of_joining BETWEEN %(from_date)s AND %(to_date)s"
    elif employee_status == "Terminated Employees":
        query += " AND e.relieving_date BETWEEN %(from_date)s AND %(to_date)s"

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

    tax_free_transport_map = get_tax_free_transportation_map(list(data_by_employee_slip.keys()))

    grouped_data = defaultdict(list)
    earnings = get_dynamic_salary_components(selected_earnings)
    component_fieldnames = [c["fieldname"] for c in earnings]

    for emp, slips in data_by_employee_slip.items():
        all_rows = [row for slip_rows in slips.values() for row in slip_rows]
        if not all_rows:
            continue

        aggregated = aggregate_salary_components(all_rows, allowed_fields=component_fieldnames)

        # Compute transport allowance exempt
        tax_free = tax_free_transport_map.get(emp, 0)
        actual_transport = aggregated.get("transport_allowance", 0)
        transport_exempt = min(actual_transport, tax_free) if tax_free > 0 else 0
        aggregated["transport_allowance_exempt"] = transport_exempt

        base = all_rows[0]
        aggregated.update({
            "employee": emp,
            "employee_name": base.employee_name,
            "department": base.department or "Other",
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
            "period": from_date.strftime('%B %Y')
        })

        grouped_data[aggregated["department"]].append(aggregated)

    final_data = []
    for dept in sorted(grouped_data.keys()):
        final_data.extend(grouped_data[dept])

    numeric_fields = component_fieldnames + ["gross_pay", "taxable_gross", "total_benefit", "transport_allowance_exempt"]
    for row in final_data:
        for field in numeric_fields:
            if row.get(field) in [None, ""]:
                row[field] = 0

    return final_data

def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months
