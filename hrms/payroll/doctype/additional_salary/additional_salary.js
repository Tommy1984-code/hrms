// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Additional Salary", {
	setup: function (frm) {
		frm.add_fetch(
			"salary_component",
			"deduct_full_tax_on_selected_payroll_date",
			"deduct_full_tax_on_selected_payroll_date",
		);

		frm.set_query("employee", function () {
			return {
				filters: {
					company: frm.doc.company,
					status: ["!=", "Inactive"],
				},
			};
		});
		
	},

	

	onload: function (frm) {
		if (frm.doc.type) {
			frm.trigger("set_component_query");
		}
	},
	is_recurring: function(frm) {
		manage_set_recurring_button(frm);
	},


	employee: function (frm) {
		if (frm.doc.employee) {
			frappe.run_serially([
				() => frm.trigger("get_employee_currency"),
				() => frm.trigger("set_company"),
			]);
		} else {
			frm.set_value("company", null);
		}
	},

	set_company: function (frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Employee",
				fieldname: "company",
				filters: {
					name: frm.doc.employee,
				},
			},
			callback: function (data) {
				if (data.message) {
					frm.set_value("company", data.message.company);
				}
			},
		});
	},

	company: function (frm) {
		frm.set_value("type", "");
		frm.trigger("set_component_query");
	},

	set_component_query: function (frm) {
		if (!frm.doc.company) return;
		let filters = { company: frm.doc.company };
		if (frm.doc.type) {
			filters.type = frm.doc.type;
		}
		frm.set_query("salary_component", function () {
			return {
				filters: filters,
			};
		});
	},

	get_employee_currency: function (frm) {
		frappe.call({
			method: "hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
			args: {
				employee: frm.doc.employee,
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("currency", r.message);
					frm.refresh_fields();
				}
			},
		});
	},
	salary_component: function (frm) {
		frm.trigger("toggle_overtime_fields"); // Toggle fields based on component

		if (!frm.doc.ref_doctype) {
			frm.trigger("get_salary_component_amount");
		}

		if (frm.doc.salary_component === "OverTime") {
			frm.trigger("calculate_overtime");
		}
	},

	rate: function (frm) {
		if (frm.doc.salary_component === "OverTime") {
			frm.trigger("calculate_overtime");
		}
	},

	working_hour: function (frm) {
		if (frm.doc.salary_component === "OverTime") {
			frm.trigger("calculate_overtime");
		}
	},

	calculate_overtime: function (frm) {
		if (frm.doc.salary_component !== "OverTime") return;

		if (!frm.doc.rate || !frm.doc.working_hour) {
			frm.set_value("amount", 0);
			frm.refresh_field("amount");
			return;
		}

		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Employee",
				filters: { name: frm.doc.employee },
				fieldname: "base",
			},
			callback: function (response) {
				if (response.message && response.message.base) {
					let base_salary = parseFloat(response.message.base);
					let working_hour = parseFloat(frm.doc.working_hour);
					let rate = parseFloat(frm.doc.rate);

					let overtime_amount = (base_salary / 208) * working_hour * rate;
					frm.set_value("amount", overtime_amount);
					frm.refresh_field("amount"); // Ensure UI updates
				}
			},
		});
	},


	// salary_component: function (frm) {
	// 	if (!frm.doc.ref_doctype) {
	// 		frm.trigger("get_salary_component_amount");
	// 	}
	// },

	get_salary_component_amount: function (frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Salary Component",
				fieldname: "amount",
				filters: {
					name: frm.doc.salary_component,
				},
			},
			callback: function (data) {
				if (data.message) {
					frm.set_value("amount", data.message.amount);
				}
			},
		});
	},
	
});

function manage_set_recurring_button(frm) {
    $(".btn-set-recurring-range").remove(); // prevent duplicate buttons

    if (frm.doc.is_recurring) {
        frm.add_custom_button(__('Set Recurring Range'), function () {
            set_recurring_range(frm);
        }).addClass('btn-set-recurring-range btn-primary');
    }
}

function set_recurring_range(frm) {
    if (!frm.doc.employee) {
        frappe.msgprint(__('Please select an Employee first.'));
        return;
    }

    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { name: frm.doc.employee },
            fieldname: ["date_of_joining", "relieving_date"]
        },
        callback: function (res) {
            if (!res.message) return;

            const { date_of_joining, relieving_date } = res.message;
            const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
            const month_range = frm.doc.recurring_months || 1;

            let from_date;

            // --- Determine from_date ---
            if (date_of_joining) {
                const joinDate = frappe.datetime.str_to_obj(date_of_joining);
                // New employee joined this month → start from joining date
                if (joinDate.getFullYear() === today.getFullYear() &&
                    joinDate.getMonth() === today.getMonth()) {
                    from_date = joinDate;
                } else {
                    // Existing employee → start from first day of current month
                    from_date = new Date(today.getFullYear(), today.getMonth(), 1);
                }
            } else {
                from_date = new Date(today.getFullYear(), today.getMonth(), 1);
            }

            // --- Calculate to_date correctly based on month_range ---
            function addMonths(date, months) {
                const d = new Date(date);
                const newMonth = d.getMonth() + months;
                d.setMonth(newMonth);
                // Adjust for month overflow
                if (d.getDate() !== date.getDate()) {
                    d.setDate(0);
                }
                return d;
            }

            // to_date = last day of the month after adding (month_range - 1) months
            let temp_date = addMonths(from_date, month_range - 1);
            let to_date = new Date(temp_date.getFullYear(), temp_date.getMonth() + 1, 0);

            // Respect relieving date if earlier
            if (relieving_date) {
                const relieveDate = frappe.datetime.str_to_obj(relieving_date);
                if (relieveDate < to_date) {
                    to_date = relieveDate;
                }
            }

            // --- Apply values ---
            frm.set_value("from_date", frappe.datetime.obj_to_str(from_date));
            frm.set_value("to_date", frappe.datetime.obj_to_str(to_date));
            frm.set_value("is_recurring", 1);

            frappe.show_alert({
                message: __(
                    "Recurring range set from {0} → {1}",
                    [frappe.datetime.obj_to_str(from_date), frappe.datetime.obj_to_str(to_date)]
                ),
                indicator: "green",
            });
        },
    });
}


