import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters, columns)
    return columns, data

def get_columns():
    return [
        {"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Data", "width": 250},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 250},
        {"label": "Month", "fieldname": "month", "fieldtype": "Data", "width": 100},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters, columns):
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    earning_component = filters.get("earning_component")
    deduction_component = filters.get("deduction_component")

    salary_component = earning_component or deduction_component
    months = get_months_in_range(from_date, to_date)
    payment_order = [
        "Advance Payment", "Performance Payment", "Third Payment",
        "Fourth Payment", "Fifth Payment"
    ]

    data = []
    dept_group = {}  # ✅ Moved outside the month loop

    for month in months:
        month_start = month.replace(day=1)
        month_end = add_months(month_start, 1) - timedelta(days=1)

        query = """
            SELECT e.name AS employee_id, e.employee_name, e.department, e.branch, e.grade, e.designation AS job_title,
                   e.employment_type, ss.name AS salary_slip, ss.end_date, ss.payment_type, sd.amount
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s AND ss.end_date >= %(month_start)s
              AND ss.company = %(company)s
              AND ss.docstatus = 1
              AND sd.salary_component = %(salary_component)s
              {employee_clause}
              {employee_name_clause}
              {department_clause}
              {payment_type_clause}
              {branch_clause}
              {grade_clause}
              {job_title_clause}
              {employment_type_clause}
            ORDER BY ss.end_date DESC, FIELD(ss.payment_type, {payment_order})
        """.format(
            employee_clause="AND ss.employee = %(employee)s" if filters.get("employee") else "",
            employee_name_clause="AND e.employee_name LIKE %(employee_name)s" if filters.get("employee_name") else "",
            department_clause="AND e.department = %(department)s" if filters.get("department") else "",
            payment_type_clause="AND ss.payment_type = %(payment_type)s" if filters.get("payment_type") else "",
            branch_clause="AND e.branch = %(branch)s" if filters.get("branch") else "",
            grade_clause="AND e.grade = %(grade)s" if filters.get("grade") else "",
            job_title_clause="AND e.designation = %(job_title)s" if filters.get("job_title") else "",
            employment_type_clause="AND e.employment_type = %(employment_type)s" if filters.get("employment_type") else "",
            payment_order=", ".join(["'{}'".format(pt) for pt in payment_order])
        )

        params = {
            "month_start": month_start,
            "month_end": month_end,
            "company": company,
            "salary_component": salary_component,
        }

        optional_fields = [
            "employee", "employee_name", "department", "payment_type",
            "branch", "grade", "job_title", "employment_type"
        ]

        for field in optional_fields:
            value = filters.get(field)
            if value:
                if field == "employee_name":
                    params[field] = f"%{value}%"
                else:
                    params[field] = value

        results = frappe.db.sql(query, params, as_dict=True)

        # Pick only the latest slip per employee for the current month
        latest_slips = {}
        for row in results:
            emp = row.employee_id
            current_index = payment_order.index(row.payment_type) if row.payment_type in payment_order else -1
            if emp not in latest_slips or current_index > payment_order.index(latest_slips[emp].payment_type):
                latest_slips[emp] = row

        # Group by department (across all months)
        for emp, row in latest_slips.items():
            dept = row.get("department") or "No Department"
            if dept not in dept_group:
                dept_group[dept] = []

            row["month"] = row["end_date"].strftime("%Y-%m")
            dept_group[dept].append({
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "month": row.month,
                "amount": row.amount or 0
            })

    # Build final data list with section headers (departments)
    for dept, employees in dept_group.items():
        # Add department header row
        data.append({
            "employee_id": f"▶ {dept}",
            "amount":None
            })
        
        # Add employee rows under the department
        for emp_data in employees:
            data.append(emp_data)

    return data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months
