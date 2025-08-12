// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Net Benefit Gross Up", {
	refresh(frm) {

 	},
    onload:function(frm){

        // Disable  adding rows in the deductions child table
        frm.fields_dict['earnings'].grid.add_new_row = false;
        frm.fields_dict['deductions'].grid.add_new_row = false;// prevent adding new rows
        
    },
});
