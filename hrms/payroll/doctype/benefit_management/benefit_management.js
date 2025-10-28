// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Benefit Management", {
    
    onload:function(frm){

        // Filter the main form's Loan Type field to show only components where loan_component is 1
        frm.set_query("benefit_type", function() {
           return {
               filters: {
                   benefit_component: 1
               }
           };
       });
       frm.fields_dict['earnings'].grid.add_new_row = false;// prevent adding new rows
    },

	refresh(frm) {
        frm.refresh_field("earnings");
	},
    setup: function(frm) {
        frm.set_query("employee", function () {
            return {
                query: "erpnext.controllers.queries.employee_query",
                filters: {
                    company: frm.doc.company,  // Ensures only employees from the selected company appear
                },
            };
        });
    },
});
