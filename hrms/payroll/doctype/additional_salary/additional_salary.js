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
	toggle_overtime_fields: function (frm) {
		let is_overtime = frm.doc.salary_component === "OverTime";

		// Show fields only if Overtime is selected
		frm.set_df_property("rate", "hidden", !is_overtime);
		frm.set_df_property("working_hour", "hidden", !is_overtime);

		// Make them mandatory only for Overtime
		frm.set_df_property("rate", "reqd", is_overtime);
		frm.set_df_property("working_hour", "reqd", is_overtime);

		// If not overtime, clear the values
		if (!is_overtime) {
			frm.set_value("rate", "");
			frm.set_value("working_hour", "");
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
