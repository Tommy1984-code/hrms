// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Loan Tracking Report"] = {
	"filters": [

		{
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
        },
		{
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 0
        },
		{
			"fieldname": "loan_type",
			"label": "Loan Type",
			"fieldtype": "Link",
			"options": "Loan Type",
			"reqd": 0
		},
   
	]
};
