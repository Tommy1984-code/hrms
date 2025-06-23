// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Termination", {
    onload:function(frm){

        // Disable  adding rows in the deductions child table
        frm.fields_dict['earnings'].grid.add_new_row = false;
        frm.fields_dict['deductions'].grid.add_new_row = false;// prevent adding new rows
       
        // frm.fields_dict['deductions'].grid.get_field('salary_component').get_query = 
        // function() { 
        //     return {
        //         filters:{
        //             'name':'Absent'
        //         }
        //     };
            
        // };
    },
    on_update: function(frm) {
        // Refresh severance table after save
        frm.refresh_field("severance_table");
        frappe.msgprint("Severance Table has been updated!");
        // Clear unsaved flag after changes applied by server
        setTimeout(() => {
            frm.dirty = false;
            frm.save_disabled = false;
            frm.page.set_indicator("");
        }, 500);  // delay to allow any async updates to finish
    },
    termination_date: function(frm) {
        // Call the server-side method when Termination Date is set
        if (frm.doc.termination_date) {
            frm.call({
                method: "generate_severance",  // Calls the backend function to generate severance table
                doc: frm.doc,
                callback: function(r) {
                    if (!r.exc) {
                        frm.refresh_field("severance_table");  // Refresh the severance table after generation
                        update_severance_total(frm);
                    }
                }
            });
        }
    },
    refresh: function(frm) {
        // Ensure calculation runs on refresh
        add_select_all_checkbox(frm);
        update_severance_total(frm);
        
        
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

// Function to handle individual grant selection and update the total severance
frappe.ui.form.on('Severance Table', {
    grant: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Update value of grant and recalculate severance total
        frappe.model.set_value(cdt, cdn, "grant", row.grant ? 1 : 0);
        
        update_severance_total(frm);  // Recalculate severance total
        frm.refresh_field('severance_table');
    },
    on_change: function(frm, cdt, cdn) {
        update_severance_total(frm);
    }
});

// Add "Select All Grants" checkbox above the Severance Table
function add_select_all_checkbox(frm) {
    // Avoid adding duplicate checkboxes
    if ($('#select_all_grants_checkbox').length === 0) {
        frm.fields_dict['severance_table'].grid.wrapper.prepend(`
            <div style="margin-bottom:0px;text-align: right;">
                <input type="checkbox" id="select_all_grants_checkbox"> 
                <label for="select_all_grants_checkbox"> Select All Grants</label>
            </div>
        `);

        // Add event listener to checkbox
        $('#select_all_grants_checkbox').change(function() {
            let checked = $(this).prop("checked");
            select_all_grants(frm, checked);
        });
    }
}

// Function to select or deselect all grants
function select_all_grants(frm, is_checked) {
    (frm.doc.severance_table || []).forEach(row => {
        frappe.model.set_value(row.doctype, row.name, 'grant', is_checked ? 1 : 0);
    });

    // Refresh the field to reflect changes
    frm.refresh_field('severance_table');
    update_severance_total(frm);  // Update total severance amount
}

function update_severance_total(frm) {
    let total = 0;
    (frm.doc.severance_table || []).forEach(row => {
        if (row.grant) {
            total += row.amount || 0;
        }
    });
    if (frm.doc.total_severance !== total) {
    frm.set_value("total_severance", total);
    frm.refresh_field('total_severance');
    }
}
