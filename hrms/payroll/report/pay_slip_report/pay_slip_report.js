// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Pay Slip Report"] = {
	"filters": [
		{
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company"
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1
        }
	]
};
