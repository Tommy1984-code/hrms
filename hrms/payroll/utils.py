import frappe


def sanitize_expression(string: str | None = None) -> str | None:
	"""
	Removes leading and trailing whitespace and merges multiline strings into a single line.

	Args:
	    string (str, None): The string expression to be sanitized. Defaults to None.

	Returns:
	    str or None: The sanitized string expression or None if the input string is None.

	Example:
	    expression = "\r\n    gross_pay > 10000\n    "
	    sanitized_expr = sanitize_expression(expression)

	"""

	if not string:
		return None

	parts = string.strip().splitlines()
	string = " ".join(parts)

	return string


@frappe.whitelist()
def get_payroll_settings_for_payment_days() -> dict:
	return frappe.get_cached_value(
		"Payroll Settings",
		None,
		[
			"payroll_based_on",
			"consider_unmarked_attendance_as",
			"include_holidays_in_total_working_days",
			"consider_marked_attendance_on_holidays",
		],
		as_dict=True,
	)

# Helper for Employee hooks
# ----------------------------
def has_base_changed(doc, base_fields):
    """
    Check if any of the base fields have changed in a document.
    
    Args:
        doc (Document): The current document (e.g., Employee)
        base_fields (list): List of field names to check
    
    Returns:
        bool: True if any field changed, False otherwise
    """
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return True  # treat as changed if new doc
    return any(getattr(doc, f) != getattr(old_doc, f) for f in base_fields)