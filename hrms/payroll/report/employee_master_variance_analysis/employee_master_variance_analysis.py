# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
from datetime import timedelta
from collections import defaultdict


def execute(filters=None):
    if filters is None:
        filters = {}

    selected_earnings = frappe.parse_json(filters.get("selected_earnings") or "[]")
    selected_deductions = frappe.parse_json(filters.get("selected_deductions") or "[]")

    columns = get_columns(selected_earnings, selected_deductions)
    data = get_data(filters, selected_earnings, selected_deductions)
    return columns, data


def _triple_column_for(component):
    """
    Given a base component dict {"label","fieldname","fieldtype","width"},
    return three column dicts: current, prev, diff
    """
    base = component.copy()
    prev = component.copy()
    diff = component.copy()

    base_label = base.get("label")
    base_field = base.get("fieldname")

    base["label"] = base_label
    base["fieldname"] = base_field

    prev["label"] = f"{base_label} (Prev)"
    prev["fieldname"] = f"{base_field}_prev"

    diff["label"] = f"{base_label} (Diff)"
    diff["fieldname"] = f"{base_field}_diff"

    # ensure types
    base["fieldtype"] = base.get("fieldtype", "Float")
    prev["fieldtype"] = prev.get("fieldtype", "Float")
    diff["fieldtype"] = diff.get("fieldtype", "Float")

    return [base, prev, diff]


def get_columns(selected_earnings=None, selected_deductions=None):
    fixed_columns = [
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Data", "width": 120},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 120},
        {"label": "Job Title", "fieldname": "job_title", "fieldtype": "Data", "width": 120},
        {"label": "Tele", "fieldname": "tele", "fieldtype": "Data", "width": 100},
        {"label": "Payment Mode", "fieldname": "payment_mode", "fieldtype": "Data", "width": 100},
        {"label": "Employment Type", "fieldname": "employment_type", "fieldtype": "Data", "width": 120},
        {"label": "Date of Hire", "fieldname": "date_of_hire", "fieldtype": "Date", "width": 100},
        {"label": "Gender", "fieldname": "gender", "fieldtype": "Data", "width": 80},
        {"label": "Tin No.", "fieldname": "tin_no", "fieldtype": "Data", "width": 120},
        {"label": "Pension ID", "fieldname": "pension_id", "fieldtype": "Data", "width": 120},
        {"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 120},
    ]

    earnings, deductions = get_dynamic_salary_components(selected_earnings, selected_deductions)

    # Expand each dynamic component into current / prev / diff
    expanded_earnings = []
    for comp in earnings:
        expanded_earnings.extend(_triple_column_for(comp))

    expanded_deductions = []
    for comp in deductions:
        expanded_deductions.extend(_triple_column_for(comp))

    # Add totals and also give them prev/diff
    totals_to_include = [
        {"label": "Total Benefit", "fieldname": "total_benefit", "fieldtype": "Float", "width": 130},
        {"label": "Taxable Gross Pay", "fieldname": "taxable_gross", "fieldtype": "Float", "width": 140},
        {"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Float", "width": 120},
        {"label": "Company Pension Cont.", "fieldname": "company_pension", "fieldtype": "Float", "width": 150},
    ]
    expanded_totals = []
    for t in totals_to_include:
        expanded_totals.extend(_triple_column_for(t))

    total_columns = [
        # For deductions totals show prev/diff too
        {"label": "Total Deduction", "fieldname": "total_deduction", "fieldtype": "Float", "width": 140},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Float", "width": 130},
    ]
    expanded_total_columns = []
    for t in total_columns:
        expanded_total_columns.extend(_triple_column_for(t))

    # Final column list: fixed + earnings(triples) + deductions(triples) + totals(triples)
    return fixed_columns + expanded_earnings + expanded_deductions + expanded_totals + expanded_total_columns


def get_dynamic_salary_components(selected_earnings=None, selected_deductions=None):
    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["name", "salary_component_abbr", "type"]
    )
    seen = set()
    earnings = []
    deductions = []
    basic_salary_column = None  # Store Basic Salary separately
    absent_column = None        # Store Absent Deduction separately

    # Initialize all special component variables
    house_allowance_column = None
    overtime_column = None
    income_tax_column = None
    pension_column = None

    for comp in components:
        abbr = comp.salary_component_abbr
        if not abbr:
            continue
        if abbr in seen:
            continue
        seen.add(abbr)

        # skip company pension abbreviation (cp) if present in scrubbed form
        if frappe.scrub(abbr) == "cp":
            continue
        # skip TA here because we handle transport differently (we still expose fieldname 'transport_allowance' later)
        if abbr.upper() == "TA":
            continue

        column = {
            "label": comp.name,
            "fieldname": frappe.scrub(abbr),
            "fieldtype": "Float",
            "width": 140
        }

        # Capture Basic Salary without inserting yet
        if abbr in ("B", "VB"):
            basic_salary_column = {
                "label": "Basic Salary",
                "fieldname": "basic_pay",
                "fieldtype": "Float",
                "width": 140
            }
            continue

        if comp.type == "Earning":
            if not selected_earnings or comp.name in selected_earnings:
                if comp.name.lower() == "overtime":
                    overtime_column = column
                    continue
                if comp.name.lower() == "house allowance":
                    house_allowance_column = column
                    continue
                earnings.append(column)

        elif comp.type == "Deduction":
            if not selected_deductions or comp.name in selected_deductions:
                if comp.name.lower() == "income tax":
                    income_tax_column = column
                    continue
                if comp.name.lower() == "pension":
                    pension_column = column
                    continue
                if comp.name.lower() == "absent":
                    absent_column = column
                    continue
                deductions.append(column)

    # Apply ordering for earnings: Basic Salary first, then Overtime, then Absent, then Transport Exempt, house allowance, then normal earnings
    ordered_earnings = []
    if basic_salary_column:
        ordered_earnings.append(basic_salary_column)
    if overtime_column:
        ordered_earnings.append(overtime_column)
    if absent_column:
        ordered_earnings.append(absent_column)

    transport_exempt_column = {
        "label": "Transport Allowance Exempt",
        "fieldname": "transport_allowance_exempt",
        "fieldtype": "Float",
        "width": 140
    }
    ordered_earnings.append(transport_exempt_column)

    if house_allowance_column:
        ordered_earnings.append(house_allowance_column)

    ordered_earnings.extend(earnings)

    # Apply ordering for deductions: Income Tax, Pension, then rest
    ordered_deductions = []
    if income_tax_column:
        ordered_deductions.append(income_tax_column)
    if pension_column:
        ordered_deductions.append(pension_column)
    ordered_deductions.extend(deductions)

    # Return lists of base components (single columns) — caller will expand into prev/diff
    return ordered_earnings, ordered_deductions


def get_active_component_map():
    components = frappe.get_all(
        "Salary Component",
        filters={"statistical_component": 0, "disabled": 0},
        fields=["salary_component_abbr", "type"]
    )
    earning_abbrs = {}
    deduction_abbrs = {}
    for c in components:
        fieldname = "basic_pay" if c.salary_component_abbr in ("B", "VB") else frappe.scrub(c.salary_component_abbr or "")
        if c.type == "Earning":
            earning_abbrs[c.salary_component_abbr] = fieldname
        elif c.type == "Deduction":
            deduction_abbrs[c.salary_component_abbr] = fieldname
    return earning_abbrs, deduction_abbrs


def aggregate_salary_components(rows, allowed_fields=None):
    """
    Aggregate salary detail rows into a dict of fieldname -> summed amount.
    allowed_fields: list of fieldnames to keep (if None, include all).
    """
    result = defaultdict(float)
    earnings_map, deductions_map = get_active_component_map()

    gross_pays = set()
    taxable_gross_pays = set()
    net_pays = set()
    total_deductions = set()
    total_benefit = 0.0

    for r in rows:
        amt = r.amount or 0
        abbr = r.abbr or r.salary_component
        fieldname = None

        if abbr in ("B", "VB"):
            fieldname = "basic_pay"
        elif r.parentfield == "earnings" and abbr in earnings_map:
            fieldname = earnings_map[abbr]
        elif r.parentfield == "deductions" and abbr in deductions_map:
            fieldname = deductions_map[abbr]

        # Only aggregate if field is allowed or allowed_fields is None
        if fieldname and (not allowed_fields or fieldname in allowed_fields):
            result[fieldname] += amt

        if abbr and abbr.upper() == "TA":
            result["transport_allowance"] = result.get("transport_allowance", 0) + amt

        # Sum total benefit (exclude base salary)
        if r.parentfield == "earnings" and abbr not in ("B", "VB"):
            total_benefit += amt

        gross_pays.add((r.salary_slip, r.gross_pay or 0))
        taxable_gross_pays.add((r.salary_slip, r.taxable_gross_pay or 0))
        net_pays.add((r.salary_slip, r.net_pay or 0))
        total_deductions.add((r.salary_slip, r.total_deduction or 0))

    result["gross_pay"] = sum(v for _, v in gross_pays)
    result["taxable_gross"] = sum(v for _, v in taxable_gross_pays)
    result["net_pay"] = sum(v for _, v in net_pays)
    result["total_deduction"] = sum(v for _, v in total_deductions)
    result["total_benefit"] = total_benefit

    if "company_pension" not in result:
        result["company_pension"] = result.get("basic_pay", 0) * 0.11

    return result


def get_tax_free_transportation_map(employee_names):
    result = {}
    if not employee_names:
        return result

    employees = frappe.get_all("Employee",
        filters={"name": ["in", employee_names]},
        fields=["name", "tax_free_transportation_amount"]
    )
    for emp in employees:
        val = emp.tax_free_transportation_amount
        try:
            num_val = float(val)
        except (ValueError, TypeError):
            num_val = 0
        result[emp.name] = num_val
    return result

def calculate_transport_exempt_from_rows(rows, tax_free_limit):
    total_transport = 0.0

    for r in rows:
        if (r.abbr or "").upper() == "TA":
            total_transport += r.amount or 0

    if isinstance(tax_free_limit, str) and tax_free_limit.lower() == "all tax":
        return 0.0

    try:
        limit = float(tax_free_limit)
    except (ValueError, TypeError):
        limit = 0.0

    return min(total_transport, limit) if limit > 0 else 0.0


def _build_prev_aggregates_for_period(from_date, to_date, company=None, filters_sql_extra="", params_extra=None):
    """
    Return a dict mapping employee -> aggregated component dict for salary slips
    whose start_date >= from_date and end_date <= to_date (previous period).
    """
    if params_extra is None:
        params_extra = {}

    query = f"""
        SELECT
            e.name AS employee, ss.name AS salary_slip, ss.start_date, ss.end_date,
            ss.gross_pay, ss.net_pay, ss.total_deduction, ss.taxable_gross_pay,
            sd.salary_component, sd.abbr, sd.amount, sd.parentfield
        FROM `tabSalary Slip` ss
        JOIN `tabEmployee` e ON ss.employee = e.name
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE ss.start_date >= %(from_date)s
          AND ss.end_date <= %(to_date)s
          AND ss.docstatus = 1
          {"AND ss.company = %(company)s" if company else ""}
          {filters_sql_extra}
    """

    params = {"from_date": from_date, "to_date": to_date}
    if company:
        params["company"] = company
    params.update(params_extra or {})

    rows = frappe.db.sql(query, params, as_dict=True)
    by_employee = defaultdict(list)
    for r in rows:
        by_employee[r.employee].append(r)

    # Aggregate per employee
    result = {}

    tax_free_transport_map = get_tax_free_transportation_map(list(by_employee.keys()))

    for emp, rows in by_employee.items():
        agg = aggregate_salary_components(rows)

        # ✅ calculate previous transport allowance exempt
        tax_limit = tax_free_transport_map.get(emp, 0)
        agg["transport_allowance_exempt"] = calculate_transport_exempt_from_rows(
            rows,
            tax_limit
        )

        result[emp] = agg

    return result


def get_data(filters, selected_earnings=None, selected_deductions=None):
    # parse filters and period
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    employee = filters.get("employee")
    payment_type_filter = filters.get("payment_type")
    branch = filters.get("branch")
    department = filters.get("department")
    grade = filters.get("grade")
    job_title = filters.get("job_title")
    employee_type = filters.get("employee_type")
    employee_status = filters.get("employee_status") or "All"

    payment_order = ["First Payment", "Second Payment", "Third Payment", "Fourth Payment", "Fifth Payment"]

    query = f"""
        SELECT
            e.name AS employee, e.employee_name, e.department, e.branch, e.designation, e.cell_number,
            e.employment_type, e.date_of_joining, e.gender, e.employee_tin_no, e.salary_mode, e.pension_id,
            ss.name AS salary_slip, ss.start_date, ss.end_date, ss.gross_pay, ss.net_pay, ss.total_deduction, ss.taxable_gross_pay,
            ss.payment_type, sd.salary_component, sd.abbr, sd.amount, sd.parentfield
        FROM `tabSalary Slip` ss
        JOIN `tabEmployee` e ON ss.employee = e.name
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE ss.start_date >= %(from_date)s
          AND ss.end_date <= %(to_date)s
          AND ss.docstatus = 1
          {"AND ss.company = %(company)s" if company else ""}
          {"AND ss.employee = %(employee)s" if employee else ""}
          {"AND ss.payment_type = %(payment_type)s" if payment_type_filter else ""}
          {"AND e.branch = %(branch)s" if branch else ""}
          {"AND e.department = %(department)s" if department else ""}
          {"AND e.grade = %(grade)s" if grade else ""}
          {"AND e.designation = %(job_title)s" if job_title else ""}
          {"AND e.employment_type = %(employee_type)s" if employee_type else ""}
    """

    # --- apply new/terminated filter ---
    if employee_status == "New Employees":
        query += " AND e.date_of_joining BETWEEN %(from_date)s AND %(to_date)s"
    elif employee_status == "Terminated Employees":
        query += " AND e.relieving_date BETWEEN %(from_date)s AND %(to_date)s"

    params = {
        "from_date": from_date,
        "to_date": to_date,
        "company": company
    }
    if employee:
        params["employee"] = employee
    if payment_type_filter:
        params["payment_type"] = payment_type_filter
    if branch:
        params["branch"] = branch
    if department:
        params["department"] = department
    if grade:
        params["grade"] = grade
    if job_title:
        params["job_title"] = job_title
    if employee_type:
        params["employee_type"] = employee_type

    # Fetch current-period rows
    results = frappe.db.sql(query, params, as_dict=True)

    # Organize rows per employee -> slip
    data_by_employee_slip = defaultdict(lambda: defaultdict(list))
    for r in results:
        emp = r.employee
        slip = r.salary_slip
        data_by_employee_slip[emp][slip].append(r)

    # Prepare tax free transport map once for all employees
    employee_names = list(data_by_employee_slip.keys())
    tax_free_transport_map = get_tax_free_transportation_map(employee_names)

    grouped_data = defaultdict(list)

    earnings, deductions = get_dynamic_salary_components(selected_earnings, selected_deductions)
    component_fieldnames = [c["fieldname"] for c in earnings + deductions]

    # Build previous period interval (previous month)
    
    prev_from = add_months(from_date.replace(day=1), -1)
    prev_to = from_date.replace(day=1) - timedelta(days=1)

    # Build previous aggregates for employees in the current result set (to minimize queries)
    # We'll call a helper to fetch all previous-period rows and aggregate per employee
    prev_aggregates = _build_prev_aggregates_for_period(prev_from, prev_to, company=company)

    # Utility: get aggregated prev for an employee (returns dict)
    def get_prev_for(emp):
        return prev_aggregates.get(emp, {})

    def process_employee(emp, slips):
        # Build all_rows following existing payment-type selection logic
        if payment_type_filter:
            all_rows = [row for slip_rows in slips.values() for row in slip_rows]
        else:
            slips_by_month = defaultdict(list)
            for slip_rows in slips.values():
                start_date = slip_rows[0].start_date
                if start_date:
                    month_key = start_date.strftime("%Y-%m")
                else:
                    month_key = "Unknown"
                slips_by_month[month_key].append(slip_rows)

            all_rows = []
            for slips_list in slips_by_month.values():
                best_slip = None
                best_priority = -1
                latest_date = None
                for slip_rows in slips_list:
                    pt = slip_rows[0].payment_type
                    prio = payment_order.index(pt) if pt in payment_order else -1

                    slip_end_date = slip_rows[0].end_date or slip_rows[0].start_date

                    if slip_end_date is not None:
                        if prio > best_priority or (prio == best_priority and (latest_date is None or slip_end_date > latest_date)):
                            best_priority = prio
                            latest_date = slip_end_date
                            best_slip = slip_rows
                    else:
                        if prio > best_priority:
                            best_priority = prio
                            latest_date = None
                            best_slip = slip_rows

                if best_slip:
                    all_rows.extend(best_slip)

        if not all_rows:
            return

        # Aggregate current period rows but only keep allowed component fields (so we match columns)
        aggregated = aggregate_salary_components(all_rows, allowed_fields=component_fieldnames)
        base = all_rows[0]
        dept = base.department or "Other"

        # Tax-free transport calculation (existing logic)
        tax_free_transport = tax_free_transport_map.get(emp, 0)
        actual_transport = aggregated.get("transport_allowance", 0)
        if isinstance(tax_free_transport, str) and tax_free_transport.lower() == "all tax":
            transport_exempt = 0  # fully taxed
        else:
            try:
                limit = int(tax_free_transport)
            except (ValueError, TypeError):
                limit = 0

            if limit > 0:
                transport_exempt = min(actual_transport, limit)
            else:
                transport_exempt = 0

        aggregated["transport_allowance_exempt"] = transport_exempt

        # Prepare previous aggregated values for this employee (previous month)
        prev_agg = get_prev_for(emp) or {}

        # Merge base fields
        row = {
            "employee": emp,
            "employee_name": base.employee_name,
            "department": dept,
            "branch": base.branch,
            "job_title": base.designation,
            "tele": base.cell_number or "",
            "payment_mode": base.salary_mode,
            "employment_type": base.employment_type,
            "date_of_hire": base.date_of_joining or "",
            "gender": base.gender or "",
            "employee_id": emp,
            "tin_no": base.employee_tin_no or "",
            "pension_id": base.pension_id or "",
            "period": from_date.strftime('%B %Y')
        }

        # For each requested component field, add current, prev and diff
        all_component_fieldnames = component_fieldnames + [
            # ensure transport allowance / transport_exempt & basic/company pensions also get prev/diff if present
            "transport_allowance", "transport_allowance_exempt"
        ]
        # totals to also provide prev/diff
        totals = ["total_benefit", "taxable_gross", "gross_pay", "company_pension", "total_deduction", "net_pay"]

        # Populate component triples
        for fname in component_fieldnames:
            cur_val = aggregated.get(fname, 0)
            prev_val = prev_agg.get(fname, 0)
            row[fname] = cur_val
            row[f"{fname}_prev"] = prev_val
            row[f"{fname}_diff"] = cur_val - prev_val

        # transport_allowance & transport_allowance_exempt
        for fname in ["transport_allowance", "transport_allowance_exempt"]:
            cur_val = aggregated.get(fname, 0)
            prev_val = prev_agg.get(fname, 0)
            row[fname] = cur_val
            row[f"{fname}_prev"] = prev_val
            row[f"{fname}_diff"] = cur_val - prev_val

        # totals
        for t in totals:
            cur_val = aggregated.get(t, 0)
            prev_val = prev_agg.get(t, 0)
            row[t] = cur_val
            row[f"{t}_prev"] = prev_val
            row[f"{t}_diff"] = cur_val - prev_val

        grouped_data[dept].append(row)

    # Process each employee group
    for emp, slips in data_by_employee_slip.items():
        process_employee(emp, slips)

    final_data = []

    # Build numeric fields list to force zeros
    # Base components single names
    base_earnings, base_deductions = get_dynamic_salary_components(selected_earnings, selected_deductions)
    base_component_fieldnames = [c["fieldname"] for c in base_earnings + base_deductions]
    numeric_fields = []
    # include triples for components
    for f in base_component_fieldnames:
        numeric_fields.extend([f, f"{f}_prev", f"{f}_diff"])
    # transport and totals
    numeric_fields.extend([
        "transport_allowance", "transport_allowance_prev", "transport_allowance_diff",
        "transport_allowance_exempt", "transport_allowance_exempt_prev", "transport_allowance_exempt_diff",
        "total_benefit", "total_benefit_prev", "total_benefit_diff",
        "taxable_gross", "taxable_gross_prev", "taxable_gross_diff",
        "gross_pay", "gross_pay_prev", "gross_pay_diff",
        "company_pension", "company_pension_prev", "company_pension_diff",
        "total_deduction", "total_deduction_prev", "total_deduction_diff",
        "net_pay", "net_pay_prev", "net_pay_diff"
    ])

    for dept in sorted(grouped_data.keys()):
        final_data.extend(grouped_data[dept])

    # Force numeric zeros
    for row in final_data:
        if not row.get("employee"):
            continue
        for field in numeric_fields:
            if row.get(field) in [None, ""]:
                row[field] = 0

    return final_data


def get_months_in_range(start_date, end_date):
    months = []
    current_month = start_date.replace(day=1)
    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)
    return months
