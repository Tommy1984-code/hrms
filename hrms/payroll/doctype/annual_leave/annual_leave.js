// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Annual Leave", {

    setup:function(frm){

        frm.set_query("employee",function(){
            return {
                query:"erpnext.controllers.queries.employee_query",
                filters:{
                    company: frm.doc.company,
                }
            }
        })

    },
	refresh(frm) {

	},
});
