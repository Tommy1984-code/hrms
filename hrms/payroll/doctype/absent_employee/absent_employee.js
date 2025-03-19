// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Absent Employee", {

    onload:function(frm){

        // Disable  adding rows in the deductions child table

        frm.fields_dict['deductions'].grid.add_new_row = false;// prevent adding new rows
       
        frm.fields_dict['deductions'].grid.get_field('salary_component').get_query = 
        function() { 
            return {
                filters:{
                    'name':'Absent'
                }
            };
            
        };
        
        
       
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

    absent_days:function(frm){
        frm.trigger('calculate_total_deduction');
    },

    deduct_single_day_amount:function(frm){
        frm.trigger('calculate_total_deduction');
    },

    calculate_total_deduction: function(frm) {
        if (frm.doc.absent_days && frm.doc.deduct_single_day_amount) {
            frm.set_value('total_deduction', frm.doc.absent_days * frm.doc.deduct_single_day_amount);
        } else {
            frm.set_value('total_deduction', 0);
        }
    },

	
});
