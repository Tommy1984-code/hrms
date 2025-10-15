// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Penalty Management", {
    refresh(frm) {
        // Disable adding new rows in the 'deductions' child table
        if(frm.fields_dict['deductions']) {
            frm.fields_dict['deductions'].grid.add_new_row = false;
        }

        // Optional: make existing rows read-only
        if(frm.fields_dict['deductions']) {
            frm.fields_dict['deductions'].grid.wrapper.find('.grid-row').each(function() {
                $(this).find('input, select, textarea').attr('readonly', true);
            });
        }
    }
});

