

frappe.ui.form.on("Loan Management", {

    onload:function(frm){

         // Filter the main form's Loan Type field to show only components where loan_component is 1
         frm.set_query("loan_type", function() {
            return {
                filters: {
                    loan_component: 1
                }
            };
        });

        // Disable  adding rows in the deductions child table

        frm.fields_dict['deductions'].grid.add_new_row = false;// prevent adding new rows
       
        frm.fields_dict['deductions'].grid.get_field('salary_component').get_query = 
        function() { 
            return {
                filters:{
                    'name': ['in', ['Healthy Loan', 'Coast Sharing Loan']] // Filter to show only the loan components
                }
            };
            
        };
    },

	refresh(frm) {
        // Refresh the deductions table to ensure it shows the latest data
        frm.refresh_field("deductions");
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
