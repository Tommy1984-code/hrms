// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Department Payroll Registery"] = {
	"filters": [
		{
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
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
            "fieldname": "payment_type",
            "label": "Payment Type",
            "fieldtype": "Select",
            "options": ["", "Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"],
            "default": ""
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
