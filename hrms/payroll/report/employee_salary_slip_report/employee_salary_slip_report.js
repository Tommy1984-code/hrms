// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Salary Slip Report"] = {
	"filters": [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee"
          },
          {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Link",
            "options": "Department"
          },
          {
            "fieldname": "grade",
            "label": "Grade",
            "fieldtype": "Link",
            "options": "Employee Grade"
          },
          {
            "fieldname": "payment_type",
            "label": "Payment Type",
            "fieldtype": "Select",
            "options": ["", "Advance Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"],
            "default": ""
          },
          {
            "fieldname": "branch",
            "label": "Branch",
            "fieldtype": "Link",
            "options": "Branch"
          },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_end()
        }
    ]
};
