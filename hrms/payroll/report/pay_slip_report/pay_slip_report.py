import frappe
from frappe.utils import formatdate

def execute(filters=None):
    filters = filters or {}

    # Build conditions
    conditions = "WHERE docstatus=1"
    values = {}
    if filters.get("from_date"):
        conditions += " AND start_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND end_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]
    if filters.get("company"):
        conditions += " AND company = %(company)s"
        values["company"] = filters["company"]

    # Fetch Salary Slip names
    slips = frappe.get_all(
        "Salary Slip",
        filters=filters,
        fields=[
            "name", "employee", "employee_name", "start_date", "end_date",
            "gross_pay", "total_deduction", "net_pay", "payment_type"
        ],
        order_by="employee asc, posting_date asc"
    )

    # Flatten earnings and deductions
    data = []
    for s in slips:
        doc = frappe.get_doc("Salary Slip", s.name)

        earnings = [{"component": e.salary_component, "amount": e.amount} for e in doc.earnings]
        deductions = [{"component": d.salary_component, "amount": d.amount} for d in doc.deductions]

        data.append({
            "employee": doc.employee,
            "employee_name": doc.employee_name,
            "start_date": formatdate(doc.start_date),
            "end_date": formatdate(doc.end_date),
            "gross_pay": doc.gross_pay,
            "total_deduction": doc.total_deduction,
            "net_pay": doc.net_pay,
            "payment_type": doc.payment_type,
            "earnings": earnings,
            "deductions": deductions
        })

    # Columns (can be empty because we will render HTML)
    columns = []

    # Return 6 values: columns, data, message, chart, report_summary, skip_total_row
    return columns, data, None, None, None, 0
