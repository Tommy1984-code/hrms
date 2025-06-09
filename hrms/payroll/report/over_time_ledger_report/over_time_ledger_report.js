// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Over Time Ledger Report"] = {
	"filters": [
		
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": "Branch",
            "fieldtype": "Link",
            "options": "Branch"
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
            "fieldname": "employee_type",
            "label": "Employee Type",
            "fieldtype": "Select",
            "options": "\nFull-Time\nPart-Time\nContract\nTemporary"
        },
        {
			"fieldname": "payment_type",
			"label": "Payment Type",
			"fieldtype": "Select",
			"options": "\nAdvance Payment\nPerformance Payment\nThird Payment\nFourth Payment\nFifth Payment"
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
