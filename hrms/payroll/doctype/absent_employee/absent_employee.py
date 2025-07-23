import frappe
from frappe.model.document import Document
from frappe.utils import getdate
import json

class AbsentEmployee(Document):
 
    def validate(self):
        self.check_duplicate_absent_record()
        self.calculate_total_deduction()
        self.add_absent_salary_component()

    def check_duplicate_absent_record(self):
        """Check if an absent record already exists for the same employee in the same month."""
        # Extract year and month from payroll_month
        payroll_month = getdate(self.payroll_month).strftime('%Y-%m')  # Format: 'YYYY-MM'

        existing_record = frappe.get_value(
            'Absent Employee',
            {
                'employee': self.employee,
                'payroll_month': ['like', f'{payroll_month}%'],  # Check for records in the same month
                'docstatus': 1  # Only check submitted documents
            },
            'name'
        )

        if existing_record:
            frappe.throw(f"An absent record for this employee already exists for the month: {payroll_month}.")

    def calculate_total_deduction(self):
        """Calculate the Absent deduction amount based on the absent days"""
        emp_base_salary = frappe.get_value("Employee",self.employee,"base")

        if not emp_base_salary:
            frappe.throw("Base Salary Is Not Found For Emploee {self.employee}")
        # Always 26 working days per month
        total_working_days = 26 

        # Calculate the deduction per day
        self.deduct_single_day_amount = emp_base_salary / total_working_days 
        #Total deduction
        self.total_deduction = self.absent_days * self.deduct_single_day_amount


    def add_absent_salary_component(self):
        """Fetch and add the 'Absent' salary component to the Deductions child table."""
        absent_component = frappe.get_value("Salary Component", {"name": "Absent"}, ["name","salary_component_abbr","amount"])

        if absent_component:
            # Check if the component is already in the deductions table
            if not any(detail.salary_component == absent_component[0] for detail in self.deductions):
                # Create a new entry for the child table
                deduction_entry = {
                    'salary_component': absent_component[0],  # Name of the component
                    'abbr': absent_component[1],
                    'amount': self.total_deduction  # Default amount
                }
                # Append to the child table
                
                self.append('deductions', deduction_entry)

@frappe.whitelist()
def add_absent_salary_component(docname):
    """Fetch and add the 'Absent' salary component to the Salary Detail child table."""
    absent_employee = frappe.get_doc("Absent Employee", docname)
    absent_component = frappe.get_value("Salary Component", {"name": "Absent"}, ["name","abbr", "default_amount"])

    if absent_component:
        absent_component_data = {
            'salary_component': absent_component[0],  # Name of the component
            'abbr': absent_component[1],
            'amount': absent_employee.total_deduction  # Set to the total deduction
        }

        # Check if the component already exists in the Salary Detail table
        if not any(comp.salary_component == 'Absent' for comp in absent_employee.salary_detail):
            absent_employee.append('salary_detail', absent_component_data)
            absent_employee.save()  # Save the document to persist changes
            return absent_component_data  # Return the added component data
            
    return None


    
                  
    



