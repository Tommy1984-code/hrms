// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Deduction Report"] = {
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
            "fieldname": "payment_type",
            "label": "Payment Type",
            "fieldtype": "Select",
            "options": ["", "Advance Payment", "Performance Payment", "Third Payment", "Fourth Payment", "Fifth Payment"],
            "default": ""
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
            "fieldname": "job_title",
            "label": "Job Title",
            "fieldtype": "Link",
            "options": "Designation"
        },
        {
            "fieldname": "employee_type",
            "label": "Employee Type",
            "fieldtype": "Select",
            "options": "\nFull-Time\nPart-Time\nContract\nTemporary"
        },
		{
            "fieldname": "mode_of_payment",
            "label": "Mode Of Payment",
            "fieldtype": "Select",
            "options": ['','Bank', 'Cash', 'Cheque'],
            "default":""
        },
        {
            "fieldname": "bank",
            "label": "Bank",
            "fieldtype": "Link",
            "options": "Bank"
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
        },
	],
   
};
