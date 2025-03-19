

frappe.ui.form.on("Loan Management", {

    onload:function(frm){

        // Disable  adding rows in the deductions child table

        frm.fields_dict['deductions'].grid.add_new_row = false;// prevent adding new rows
       
        frm.fields_dict['deductions'].grid.get_field('salary_component').get_query = 
        function() { 
            return {
                filters:{
                    'name':'Loan'
                }
            };
            
        };
        
       
    },
	refresh(frm) {

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
    }
});
