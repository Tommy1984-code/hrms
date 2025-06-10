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
    mode_of_payment = filters.get("mode_of_payment")
    company = filters.get("company")
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

    # 1) Fetch all relevant salary detail rows for the range
    all_results = []
    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
            SELECT e.name AS employee, e.employee_name, e.department, e.designation, e.branch, e.grade,
                   ss.bank_name AS bank, ss.mode_of_payment, ss.payment_type,
                   ss.name AS salary_slip, ss.gross_pay, ss.net_pay, ss.total_deduction,
                   ss.end_date,
                   sd.salary_component, sd.abbr, sd.amount, sd.parentfield
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s
              AND ss.end_date >= %(month_start)s
              AND ss.docstatus = 1
              {clauses}
            ORDER BY ss.end_date DESC
        """.format(clauses=" ".join([
            "AND ss.company = %(company)s" if company else "",
            "AND ss.mode_of_payment = %(mode_of_payment)s" if mode_of_payment else "",
            "AND ss.employee = %(employee)s" if employee else "",
            "AND ss.payment_type = %(payment_type)s" if payment_type else "",
            "AND e.branch = %(branch)s" if branch else "",
            "AND e.department = %(department)s" if department else "",
            "AND e.grade = %(grade)s" if grade else "",
            "AND e.designation = %(job_title)s" if job_title else "",
            "AND e.employment_type = %(employee_type)s" if employee_type else "",
            "AND ss.bank_name = %(bank)s" if bank else "",
        ]))

        params = {
            "month_start": month_start,
            "month_end": month_end,
            **({ "company": company } if company else {}),
            **({ "mode_of_payment": mode_of_payment } if mode_of_payment else {}),
            **({ "employee": employee } if employee else {}),
            **({ "payment_type": payment_type } if payment_type else {}),
            **({ "branch": branch } if branch else {}),
            **({ "department": department } if department else {}),
            **({ "grade": grade } if grade else {}),
            **({ "job_title": job_title } if job_title else {}),
            **({ "employee_type": employee_type } if employee_type else {}),
            **({ "bank": bank } if bank else {}),
        }

        rows = frappe.db.sql(query, params, as_dict=True)
        all_results.extend(rows)

    # 2) Select one slip per employee per month based on priority and aggregate components
    monthly_slips = {}  # key = emp + YYYY-MM, value = dict with amounts & priority
    for row in all_results:
        emp = row.employee
        month_key = f"{emp}-{row.end_date.strftime('%Y-%m')}"
        priority = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1

        if month_key not in monthly_slips or priority > monthly_slips[month_key]["_priority"]:
            monthly_slips[month_key] = {
                "employee": emp,
                "employee_name": " ".join(row.employee_name.split()[:2]),
                "department": row.department or "No Department",
                "designation": row.designation,
                "mode_of_payment": row.mode_of_payment,
                "bank": row.bank,
                "basic": 0, "hardship": 0, "overtime": 0,
                "commission": 0, "incentive": 0,
                "income_tax": 0, "employee_pension": 0,
                "absence": 0, "other_deduction": 0,
                "gross_pay": row.gross_pay,
                "net_pay": row.net_pay,
                "total_deduction": row.total_deduction,
                "_priority": priority
            }

        # If this slip is the one selected (highest priority)
        if monthly_slips[month_key]["_priority"] == priority:
            amt = row.amount or 0
            comp = row.abbr or row.salary_component
            pf = row.parentfield
            tgt = monthly_slips[month_key]
            if pf == "earnings":
                if comp in ("B", "VB"):
                    tgt["basic"] += amt
                elif comp == "HDA":
                    tgt["hardship"] += amt
                elif comp == "OT":
                    tgt["overtime"] += amt
                elif comp == "C":
                    tgt["commission"] += amt
                elif comp == "PP":
                    tgt["incentive"] += amt
            elif pf == "deductions":
                if comp == "IT":
                    tgt["income_tax"] += amt
                elif comp == "PS":
                    tgt["employee_pension"] += amt
                elif comp == "ABT":
                    tgt["absence"] += amt
                else:
                    tgt["other_deduction"] += amt

    # 3) Sum up across months per employee
    final_emps = {}
    for data in monthly_slips.values():
        emp = data["employee"]
        if emp not in final_emps:
            final_emps[emp] = data.copy()
        else:
            tgt = final_emps[emp]
            for field in [
                "basic", "hardship", "overtime", "commission", "incentive",
                "income_tax", "employee_pension", "absence", "other_deduction",
                "gross_pay", "net_pay", "total_deduction"
            ]:
                tgt[field] += data[field]

    # 4) Build department-based output table
    department_rows = {}
    for emp_data in final_emps.values():
        emp_data["company_pension"] = emp_data["basic"] * 0.11
        emp_data["taxable_gross"] = emp_data["gross_pay"]
        dept = emp_data["department"]
        department_rows.setdefault(dept, []).append(emp_data)

    # 5) Format final data
    data = []
    for dept in sorted(department_rows.keys()):
        data.append([f"▶ {dept}"] + [None] * (num_columns - 1))
        for g in department_rows[dept]:
            row = [
                g["employee_name"],
                g["basic"], g["absence"], g["hardship"], g["overtime"],
                g["commission"], g["incentive"], g["taxable_gross"], g["gross_pay"],
                g["company_pension"], g["income_tax"], g["employee_pension"],
                g["other_deduction"], g["total_deduction"], g["net_pay"]
            ]
            # Add designation only for Bank payment mode
            if mode_of_payment == "Bank":
                row.append(g["designation"])
            else:
                row.append("")
            data.append(row)

    return data

def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months
