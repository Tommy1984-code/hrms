import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters, columns)
    return columns, data

def get_columns(filters=None):
    columns = [
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
    ]
    if filters and filters.get("mode_of_payment") == "Bank":
        columns.append({"label": "Title", "fieldname": "title", "fieldtype": "Data", "width": 120})
    else:
        columns.append({"label": "Signature", "fieldname": "signature", "fieldtype": "Data", "width": 100})
    return columns

def get_data(filters, columns):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    mode_of_payment = filters.get("mode_of_payment")
    employee = filters.get("employee")
    payment_type = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")
    bank = filters.get("bank")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    payment_order = ["Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]
    num_columns = len(columns)

    department_rows = {}

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
            SELECT e.name AS employee, e.employee_name, e.department, e.designation, e.branch, e.grade, e.bank_name, e.employment_type,
                   ss.name AS salary_slip, ss.gross_pay, ss.net_pay, ss.mode_of_payment, ss.payment_type,
                   ss.total_deduction, ss.end_date,
                   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
              {company_clause}
              {payment_mode_clause}
              {employee_clause}
              {payment_type_clause}
              {branch_clause}
              {department_clause}
              {grade_clause}
              {job_title_clause}
              {employee_type_clause}
              {bank_clause}
            ORDER BY ss.end_date DESC
        """.format(
            company_clause="AND ss.company = %(company)s" if company else "",
            payment_mode_clause="AND ss.mode_of_payment = %(mode_of_payment)s" if mode_of_payment else "",
            employee_clause="AND ss.employee = %(employee)s" if employee else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if payment_type else "",
            branch_clause="AND e.branch = %(branch)s" if branch else "",
            department_clause="AND e.department = %(department)s" if department else "",
            grade_clause="AND e.grade = %(grade)s" if grade else "",
            job_title_clause="AND e.designation = %(job_title)s" if job_title else "",
            employee_type_clause="AND e.employment_type = %(employee_type)s" if employee_type else "",
            bank_clause="AND ss.bank_name = %(bank)s" if bank else ""
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company": company,
        }

        optional_fields = [
            "mode_of_payment",
            "employee",
            "payment_type",
            "branch",
            "department",
            "grade",
            "job_title",
            "employee_type",
            "bank"
        ]

        for field in optional_fields:
            value = locals().get(field)
            if value:
                params[field] = value

        results = frappe.db.sql(query, params, as_dict=True)

        # Get latest salary slip per employee for that month
        latest_slips = {}
        for row in results:
            emp = row.employee
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
            if emp not in latest_slips or current_index > payment_order.index(latest_slips[emp].payment_type):
                latest_slips[emp] = row

        grouped_data = {}
        for row in results:
            if row.employee not in latest_slips or row.salary_slip != latest_slips[row.employee].salary_slip:
                continue

            if row.salary_slip not in grouped_data:
                grouped_data[row.salary_slip] = {
                    "employee_name": " ".join(row.employee_name.split()[:2]),
                    "department": row.department,
                    "designation": row.designation,
                    "month_label": row.end_date.strftime("%B"),  # <-- Show month
                    "gross_pay": row.gross_pay,
                    "net_pay": row.net_pay,
                    "total_deduction": row.total_deduction,
                    "basic": 0, "hardship": 0, "overtime": 0, "commission": 0,
                    "incentive": 0, "income_tax": 0, "employee_pension": 0,
                    "absence": 0, "other_deduction": 0
                }

            comp = row.abbr or row.salary_component
            val = row.amount or 0
            field = row.parentfield

            if field == "earnings":
                if comp in ('B', 'VB'):
                    grouped_data[row.salary_slip]["basic"] += val
                elif comp == 'HDA':
                    grouped_data[row.salary_slip]["hardship"] += val
                elif comp == 'OT':
                    grouped_data[row.salary_slip]["overtime"] += val
                elif comp == 'C':
                    grouped_data[row.salary_slip]["commission"] += val
                elif comp == 'PP':
                    grouped_data[row.salary_slip]["incentive"] += val
            elif field == "deductions":
                if comp == 'IT':
                    grouped_data[row.salary_slip]["income_tax"] += val
                elif comp == 'PS':
                    grouped_data[row.salary_slip]["employee_pension"] += val
                elif comp == 'ABT':
                    grouped_data[row.salary_slip]["absence"] += val
                else:
                    grouped_data[row.salary_slip]["other_deduction"] += val

        # Merge rows under department
        for slip, g in grouped_data.items():
            g["company_pension"] = g["basic"] * 0.11
            g["taxable_gross"] = g["gross_pay"]
            dept = g.get("department") or "No Department"
            if dept not in department_rows:
                department_rows[dept] = []
            department_rows[dept].append(g)

    # Now create final data table
    data = []
    for dept, employees in sorted(department_rows.items()):
        data.append([f"▶ {dept}"] + [None] * (num_columns - 1))
        for g in employees:
            row = [
                f"{g['employee_name']}",
                g["basic"], g["absence"], g["hardship"], g["overtime"],
                g["commission"], g["incentive"], g["taxable_gross"], g["gross_pay"],
                g["company_pension"], g["income_tax"], g["employee_pension"],
                g["other_deduction"], g["total_deduction"], g["net_pay"]
            ]
            row.append(g["designation"] if mode_of_payment == "Bank" else "")
            data.append(row)

    return data

def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months
