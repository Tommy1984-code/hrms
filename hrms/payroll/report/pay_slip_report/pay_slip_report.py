# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Frappe Technologies
import frappe
from frappe.utils import getdate

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")

    conditions = {"docstatus": 1}

    if from_date and to_date:
        conditions["start_date"] = [">=", from_date]
        conditions["end_date"] = ["<=", to_date]

    if company:
        conditions["company"] = company

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=conditions,
        order_by="employee asc, start_date asc",
        pluck="name"
    )

    html_blocks = []

    for slip_name in salary_slips:
        slip = frappe.get_doc("Salary Slip", slip_name)

        html = frappe.render_template(
            "your_app/your_app/report/bulk_payslip_print/payslip_template.html",
            {"doc": slip, "frappe": frappe}
        )

        html_blocks.append(html)

    final_html = """
    <style>
        @media print {
            .page-break {
                page-break-after: always;
            }
        }
    </style>
    """ + '<div class="page-break"></div>'.join(html_blocks)

    return [], [], final_html

