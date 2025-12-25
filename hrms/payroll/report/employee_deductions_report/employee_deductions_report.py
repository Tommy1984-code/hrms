# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from collections import defaultdict


def execute(filters=None):
    if filters is None:
        filters = {}

    selected_deductions = frappe.parse_json(filters.get("selected_deductions") or "[]")

    columns = get_columns(selected_deductions)
    data = get_data(filters, selected_deductions)
    return columns, data


def get_columns(selected_deductions=None):
    fixed_columns = [
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Data", "width": 120},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
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

    basic_salary, deductions = get_dynamic_salary_components(selected_deductions)

    total_columns = [
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Float", "width": 140},
    ]

    return fixed_columns + basic_salary + deductions + total_columns


def get_dynamic_salary_components(selected_deductions=None):
    PRIORITY_DEDUCTIONS = ["Income Tax", "pension"]

    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["name", "salary_component_abbr", "type"]
    )

    basic_salary = []
    deductions = []
    seen = set()

    for comp in components:
        abbr = comp.salary_component_abbr
        if abbr in seen:
            continue
        seen.add(abbr)

        if abbr in ("B", "VB"):
            basic_salary.append({
                "label": "Basic Salary",
                "fieldname": "basic_pay",
                "fieldtype": "Float",
                "width": 140
            })
            continue

        if comp.type == "Deduction":
            if not selected_deductions or comp.name in selected_deductions:
                deductions.append({
                    "label": comp.name,
                    "fieldname": frappe.scrub(abbr),
                    "fieldtype": "Float",
                    "width": 140
                })

    # Basic Salary is already first — force Income Tax & Pension next
    deductions.sort(
        key=lambda d: (
            PRIORITY_DEDUCTIONS.index(d["label"])
            if d["label"] in PRIORITY_DEDUCTIONS
            else len(PRIORITY_DEDUCTIONS)
        )
    )

    return basic_salary, deductions


def get_active_component_map():
    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["salary_component_abbr", "type"]
    )

    deduction_abbrs = {}
    for c in components:
        if c.type == "Deduction":
            deduction_abbrs[c.salary_component_abbr] = frappe.scrub(c.salary_component_abbr)

    return deduction_abbrs


def aggregate_salary_components(rows, allowed_fields=None):
    result = defaultdict(float)
    deduction_map = get_active_component_map()
    total_deductions = set()

    for r in rows:
        amt = r.amount or 0
        abbr = r.abbr or r.salary_component

        if abbr in ("B", "VB"):
            if not allowed_fields or "basic_pay" in allowed_fields:
                result["basic_pay"] += amt

        elif r.parentfield == "deductions" and abbr in deduction_map:
            fieldname = deduction_map[abbr]
            if not allowed_fields or fieldname in allowed_fields:
                result[fieldname] += amt

        total_deductions.add((r.salary_slip, r.total_deduction or 0))

    result["total_deduction"] = sum(v for _, v in total_deductions)
    return result


def get_data(filters, selected_deductions=None):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")

    employee = filters.get("employee")
    payment_type = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    employee_type = filters.get("employee_type")
    employee_status = filters.get("employee_status")

    conditions = []

    if employee:
        conditions.append("ss.employee = %(employee)s")

    if payment_type:
        conditions.append("ss.payment_type = %(payment_type)s")

    if branch:
        conditions.append("e.branch = %(branch)s")

    if department:
        conditions.append("e.department = %(department)s")

    if grade:
        conditions.append("e.grade = %(grade)s")

    if employee_type:
        conditions.append("e.employment_type = %(employee_type)s")

    if employee_status == "New Employees":
        conditions.append("e.date_of_joining BETWEEN %(from_date)s AND %(to_date)s")

    elif employee_status == "Terminated Employees":
        conditions.append("e.relieving_date IS NOT NULL")

    query = """
        SELECT
            e.name AS employee, e.employee_name, e.department, e.branch,
            e.designation, e.cell_number, e.employment_type,
            e.date_of_joining, e.gender, e.employee_tin_no,
            e.salary_mode, e.pension_id,
            ss.name AS salary_slip, ss.start_date, ss.end_date,
            ss.total_deduction,
            sd.salary_component, sd.abbr, sd.amount, sd.parentfield
        FROM `tabSalary Slip` ss
        JOIN `tabEmployee` e ON ss.employee = e.name
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE ss.start_date >= %(from_date)s
          AND ss.end_date <= %(to_date)s
          AND ss.docstatus = 1
          {company_filter}
          {extra_conditions}
    """.format(
        company_filter="AND ss.company = %(company)s" if company else "",
        extra_conditions="AND " + " AND ".join(conditions) if conditions else ""
    )

    params = {
        "from_date": from_date,
        "to_date": to_date,
        "company": company,
        "employee": employee,
        "payment_type": payment_type,
        "branch": branch,
        "department": department,
        "grade": grade,
        "employee_type": employee_type,
    }

    results = frappe.db.sql(query, params, as_dict=True)

    data_by_employee = defaultdict(list)
    for r in results:
        data_by_employee[r.employee].append(r)

    basic_salary, deductions = get_dynamic_salary_components(selected_deductions)
    component_fieldnames = [c["fieldname"] for c in basic_salary + deductions]

    final_data = []

    for emp, rows in data_by_employee.items():
        aggregated = aggregate_salary_components(rows, allowed_fields=component_fieldnames)
        base = rows[0]

        aggregated.update({
            "employee": emp,
            "employee_name": base.employee_name,
            "department": base.department,
            "branch": base.branch,
            "job_title": base.designation,
            "tele": base.cell_number or "",
            "payment_mode": base.salary_mode,
            "employment_type": base.employment_type,
            "date_of_hire": base.date_of_joining,
            "gender": base.gender,
            "tin_no": base.employee_tin_no,
            "pension_id": base.pension_id,
            "period": from_date.strftime("%B %Y")
        })

        final_data.append(aggregated)

    numeric_fields = component_fieldnames + ["total_deduction"]
    for row in final_data:
        for f in numeric_fields:
            row[f] = row.get(f) or 0

    return final_data


def get_months_in_range(start_date, end_date):
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months.append(current)
        current = add_months(current, 1)
    return months
