// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Loan Tracking Report"] = {
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
            "options": "Employee",
            "reqd": 1
        },
		{
            "fieldname": "loan_type",
            "label": "Loan Type",
            "fieldtype": "Link",
            "options": "Salary Component",
            "reqd": 1,
            "get_query": function() {
                return {
                    filters: {
                        "loan_component": 1   // Only show Salary Components marked as Loan
                    }
                };
            }
        }
        
        
   
	]
    
};
