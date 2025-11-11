// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Master List"] = {
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
            "options": ["", "First Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"],
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
            "fieldname": "employee_type",
            "label": "Employee Type",
            "fieldtype": "Select",
            "options": "\nFull-Time\nPart-Time\nContract\nTemporary"
        },
        {
          fieldname: "employee_status",
          label: __("Employee Status"),
          fieldtype: "Select",
          options: "\nAll\nNew Employees\nTerminated Employees",
          default: "All"
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
        {
            fieldname: "selected_earnings",
            label: "Earnings", // Keep it clean
            fieldtype: "MultiSelectList",
            get_data: async function (txt) {
              const components = await frappe.db.get_list("Salary Component", {
                filters: { type: "Earning", disabled: 0 },
                fields: ["name"],
                limit: 100
              });
      
              const search = txt?.toLowerCase() || "";
              return components
                .map(c => ({ label: c.name, value: c.name }))
                .filter(opt => opt.label.toLowerCase().includes(search));
            },
            default: [], // Ensures no 'undefined'
            reqd: 0, // Not required
            on_change: () => frappe.query_report.refresh()
          },
          {
            fieldname: "selected_deductions",
            label: "Deductions", // Keep it clean
            fieldtype: "MultiSelectList",
            get_data: async function (txt) {
              const components = await frappe.db.get_list("Salary Component", {
                filters: { type: "Deduction", disabled: 0 },
                fields: ["name"],
                limit: 100
              });
      
              const search = txt?.toLowerCase() || "";
              return components
                .map(c => ({ label: c.name, value: c.name }))
                .filter(opt => opt.label.toLowerCase().includes(search));
            },
            default: [], // Ensures no 'undefined'
            reqd: 0,
            on_change: () => frappe.query_report.refresh()
          }
	],
    onload: async function (report) {
        const earnings = await frappe.db.get_list("Salary Component", {
          filters: { type: "Earning", disabled: 0 },
          fields: ["name"],
          limit: 100
        });
        const deductions = await frappe.db.get_list("Salary Component", {
          filters: { type: "Deduction", disabled: 0 },
          fields: ["name"],
          limit: 100
        });
      
        const earningNames = earnings.map(e => e.name);
        const deductionNames = deductions.map(d => d.name);

      
        // Delay setting values until filter UI is ready
        frappe.after_ajax(() => {
          frappe.query_report.set_filter_value("selected_earnings", earningNames);
          frappe.query_report.set_filter_value("selected_deductions", deductionNames);
        });
      }
      
};