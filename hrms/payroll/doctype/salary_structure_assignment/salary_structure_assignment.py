# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_link_to_form, getdate

from hrms.payroll.doctype.payroll_period.payroll_period import get_payroll_period


class DuplicateAssignment(frappe.ValidationError):
	pass


class SalaryStructureAssignment(Document):
	def validate(self):
		# self.set_base_salary()
		self.validate_dates()
		self.validate_company()
		self.validate_income_tax_slab()
		self.set_payroll_payable_account()
		
		if not self.get("payroll_cost_centers"):
			self.set_payroll_cost_centers()

		self.validate_cost_centers()
		self.warn_about_missing_opening_entries()
    
	def on_update_after_submit(self):
		self.validate_cost_centers()

	def validate_dates(self):
		joining_date, relieving_date = frappe.db.get_value(
			"Employee", self.employee, ["date_of_joining", "relieving_date"]
		)

		if self.from_date:
			if frappe.db.exists(
				"Salary Structure Assignment",
				{"employee": self.employee, 
	             "from_date": self.from_date,
				 "payment_type": self.payment_type,  # my code check against payment type 
				 "docstatus": 1
				},
			):
				frappe.throw(
					_("Salary Structure Assignment for Employee {0} with payment Type{1} already exists for from Date {2}").
					  format(self.employee,self.payment_type,self.from_date), DuplicateAssignment
				)

			if joining_date and getdate(self.from_date) < joining_date:
				frappe.throw(
					_("From Date {0} cannot be before employee's joining Date {1}").format(
						self.from_date, joining_date
					)
				)

			# flag - old_employee is for migrating the old employees data via patch
			if relieving_date and getdate(self.from_date) > relieving_date and not self.flags.old_employee:
				frappe.throw(
					_("From Date {0} cannot be after employee's relieving Date {1}").format(
						self.from_date, relieving_date
					)
				)

	def validate_company(self):
		salary_structure_company = frappe.db.get_value(
			"Salary Structure", self.salary_structure, "company", cache=True
		)
		if self.company != salary_structure_company:
			frappe.throw(
				_("Salary Structure {0} does not belong to company {1}").format(
					frappe.bold(self.salary_structure), frappe.bold(self.company)
				)
			)
	#my code to set Base in Salary Structure assignment from Employee    
	def set_base_salary(self):
		base_salary= frappe.db.get_value("Employee",self.employee,"base",cache=True)
		if base_salary:
			self.base = base_salary
		else:
			frappe.throw(_("Base Salary Not Found for Employee{0}").format(self.employee))


	def validate_income_tax_slab(self):
		tax_component = get_tax_component(self.salary_structure)
		if tax_component and not self.income_tax_slab:
			frappe.throw(
				_(
					"Income Tax Slab is mandatory since the Salary Structure {0} has a tax component {1}"
				).format(
					get_link_to_form("Salary Structure", self.salary_structure), frappe.bold(tax_component)
				),
				exc=frappe.MandatoryError,
				title=_("Missing Mandatory Field"),
			)

		if not self.income_tax_slab:
			return

		income_tax_slab_currency = frappe.db.get_value("Income Tax Slab", self.income_tax_slab, "currency")
		if self.currency != income_tax_slab_currency:
			frappe.throw(
				_("Currency of selected Income Tax Slab should be {0} instead of {1}").format(
					self.currency, income_tax_slab_currency
				)
			)

	def set_payroll_payable_account(self):
		if not self.payroll_payable_account:
			payroll_payable_account = frappe.db.get_value(
				"Company", self.company, "default_payroll_payable_account"
			)
			if not payroll_payable_account:
				payroll_payable_account = frappe.db.get_value(
					"Account",
					{
						"account_name": _("Payroll Payable"),
						"company": self.company,
						"account_currency": frappe.db.get_value("Company", self.company, "default_currency"),
						"is_group": 0,
					},
				)
			self.payroll_payable_account = payroll_payable_account

	@frappe.whitelist()
	def set_payroll_cost_centers(self):
		self.payroll_cost_centers = []
		default_payroll_cost_center = self.get_payroll_cost_center()
		if default_payroll_cost_center:
			self.append(
				"payroll_cost_centers", {"cost_center": default_payroll_cost_center, "percentage": 100}
			)

	def get_payroll_cost_center(self):
		payroll_cost_center = frappe.db.get_value("Employee", self.employee, "payroll_cost_center")
		if not payroll_cost_center and self.department:
			payroll_cost_center = frappe.db.get_value("Department", self.department, "payroll_cost_center")

		return payroll_cost_center

	def validate_cost_centers(self):
		if not self.get("payroll_cost_centers"):
			return

		total_percentage = 0
		for entry in self.payroll_cost_centers:
			company = frappe.db.get_value("Cost Center", entry.cost_center, "company")
			if company != self.company:
				frappe.throw(
					_("Row {0}: Cost Center {1} does not belong to Company {2}").format(
						entry.idx, frappe.bold(entry.cost_center), frappe.bold(self.company)
					),
					title=_("Invalid Cost Center"),
				)

			total_percentage += flt(entry.percentage)

		if total_percentage != 100:
			frappe.throw(_("Total percentage against cost centers should be 100"))

	def warn_about_missing_opening_entries(self):
		if (
			self.are_opening_entries_required()
			and not self.taxable_earnings_till_date
			and not self.tax_deducted_till_date
		):
			msg = _("Could not find any salary slip(s) for the employee {0}").format(self.employee)
			msg += "<br><br>"
			msg += _(
				"Please specify {0} and {1} (if any), for the correct tax calculation in future salary slips."
			).format(
				frappe.bold(_("Taxable Earnings Till Date")),
				frappe.bold(_("Tax Deducted Till Date")),
			)
			frappe.msgprint(
				msg,
				indicator="orange",
				title=_("Missing Opening Entries"),
			)

	@frappe.whitelist()
	def are_opening_entries_required(self) -> bool:
		if self.has_emp_joined_after_payroll_period_start() and not self.has_existing_salary_slips():
			return True
		else:
			if not self.docstatus.is_draft() and (
				self.taxable_earnings_till_date or self.tax_deducted_till_date
			):
				return True
			return False

	def has_existing_salary_slips(self) -> bool:
		return bool(
			frappe.db.exists(
				"Salary Slip",
				{"employee": self.employee, "docstatus": 1},
			)
		)

	def has_emp_joined_after_payroll_period_start(self) -> bool:
		date_of_joining = getdate(frappe.db.get_value("Employee", self.employee, "date_of_joining"))
		payroll_period = get_payroll_period(self.from_date, self.from_date, self.company)
		if not payroll_period or date_of_joining > getdate(payroll_period.start_date):
			return True
		return False
     

#my code seting payment type
from datetime import datetime
@frappe.whitelist()
def set_payment_type_based_on_advance(employee,from_date):
	# Validate input
	if not employee or not from_date:
		return None  # Return None if inputs are not valid
	# Convert from_date to a datetime object for processing
	from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
	# Logic to determine the payment type
	payment_type = determine_payment_type(employee, from_date_dt)
	return payment_type

def determine_payment_type(employee, from_date):
	# Check if there's an existing assignment for this employee
	existing_assignments = frappe.get_all('Salary Structure Assignment', filters={
        'employee': employee,
        'from_date': from_date,
		'docstatus':1
    })

	# If no existing assignment, set payment type to Advance Payment
	if not existing_assignments:
		return "Advance Payment"
	
	# If there is an existing assignment, set payment type to Performance Payment
	return "Performance Payment"
    



def get_assigned_salary_structure(employee, on_date):
	if not employee or not on_date:
		return None
	salary_structure = frappe.db.sql(
		"""
		select salary_structure from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and %(on_date)s >= from_date order by from_date desc limit 1""",
		{
			"employee": employee,
			"on_date": on_date,
		},
	)
	return salary_structure[0][0] if salary_structure else None


@frappe.whitelist()
def get_employee_currency(employee):
	employee_currency = frappe.db.get_value("Salary Structure Assignment", {"employee": employee}, "currency")
	if not employee_currency:
		frappe.throw(
			_("There is no Salary Structure assigned to {0}. First assign a Salary Stucture.").format(
				employee
			)
		)
	return employee_currency


def get_tax_component(salary_structure: str) -> str | None:
	salary_structure = frappe.get_cached_doc("Salary Structure", salary_structure)
	for d in salary_structure.deductions:
		if cint(d.variable_based_on_taxable_salary) and not d.formula and not flt(d.amount):
			return d.salary_component
	return None
