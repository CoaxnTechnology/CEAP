HR_TOOLS = [
    {
        "name": "apply_leave",
        "description": "Submit a leave application for the current user",
        "parameters": {
            "type": "object",
            "properties": {
                "leave_type": {
                    "type": "string",
                    "enum": ["annual", "sick", "personal", "maternity", "paternity"],
                    "description": "Type of leave"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for leave"
                }
            },
            "required": ["leave_type", "start_date", "end_date"]
        }
    },
    {
        "name": "get_leave_balance",
        "description": "Check remaining leave balance for the current user",
        "parameters": {
            "type": "object",
            "properties": {
                "leave_type": {
                    "type": "string",
                    "enum": ["annual", "sick", "personal", "all"],
                    "description": "Type of leave to check, or 'all' for everything"
                }
            },
            "required": ["leave_type"]
        }
    },
    {
        "name": "list_my_leaves",
        "description": "List all leave requests for the current user",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "approved", "rejected", "all"],
                    "description": "Filter by status"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "get_attendance",
        "description": "Get attendance records for the current user for a date range",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "mark_attendance",
        "description": "Mark attendance check-in or check-out for the current user",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check_in", "check_out"],
                    "description": "Whether to check in or check out"
                },
                "timestamp": {
                    "type": "string",
                    "description": "Time in HH:MM format, defaults to now"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_payslip",
        "description": "Retrieve payslip information. Looks up payslip documents indexed in the system.",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Payslip period in YYYY-MM format, e.g. 2026-05"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "search_hr_policy",
        "description": "Search HR policy documents for answers to policy questions",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The policy question to search for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_employee_info",
        "description": "Get current user's employee profile information",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_pending_approvals",
        "description": "Get pending approval requests that need the current user's action",
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["approver", "requester"],
                    "description": "View pending approvals as approver or view your own requests"
                }
            },
            "required": ["role"]
        }
    },
    {
        "name": "approve_or_reject_request",
        "description": "Approve or reject a pending approval request",
        "parameters": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string",
                    "description": "ID of the approval request"
                },
                "decision": {
                    "type": "string",
                    "enum": ["approved", "rejected"],
                    "description": "Your decision"
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment"
                }
            },
            "required": ["request_id", "decision"]
        }
    },
]

ACCOUNTING_TOOLS = [
    {
        "name": "create_invoice",
        "description": "Create a new invoice record manually",
        "parameters": {
            "type": "object",
            "properties": {
                "invoice_number": {"type": "string", "description": "Invoice number"},
                "vendor_name": {"type": "string", "description": "Vendor/supplier name"},
                "date": {"type": "string", "description": "Invoice date in YYYY-MM-DD format"},
                "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                "total_amount": {"type": "number", "description": "Total invoice amount"},
                "tax": {"type": "number", "description": "Tax amount"},
                "currency": {"type": "string", "description": "Currency code (e.g. USD, EUR)"}
            },
            "required": ["invoice_number", "vendor_name", "date", "total_amount"]
        }
    },
    {
        "name": "extract_invoice_data",
        "description": "Extract structured data from an uploaded invoice PDF file",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The file_id of the uploaded invoice PDF"
                }
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "list_invoices",
        "description": "List invoices filtered by status",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "paid", "overdue", "cancelled", "all"],
                    "description": "Filter by invoice status"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "mark_invoice_paid",
        "description": "Mark an invoice as paid",
        "parameters": {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "string",
                    "description": "The invoice ID"
                },
                "payment_date": {
                    "type": "string",
                    "description": "Payment date in YYYY-MM-DD format"
                }
            },
            "required": ["invoice_id", "payment_date"]
        }
    },
    {
        "name": "submit_expense",
        "description": "Submit an expense claim",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["travel", "meals", "office_supplies", "software", "transport", "other"],
                    "description": "Expense category"
                },
                "amount": {
                    "type": "number",
                    "description": "Expense amount"
                },
                "description": {
                    "type": "string",
                    "description": "Description of the expense"
                },
                "receipt_file_id": {
                    "type": "string",
                    "description": "Optional file_id of uploaded receipt"
                }
            },
            "required": ["category", "amount", "description"]
        }
    },
    {
        "name": "list_expenses",
        "description": "List expense claims for the current user",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "approved", "rejected", "all"],
                    "description": "Filter by status"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "get_financial_summary",
        "description": "Get a monthly financial summary showing total invoices, paid, pending, and expenses",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": "Month in YYYY-MM format, defaults to current month"
                }
            },
            "required": []
        }
    },
    {
        "name": "send_payment_reminder",
        "description": "Send payment reminder for overdue invoices",
        "parameters": {
            "type": "object",
            "properties": {
                "vendor_name": {
                    "type": "string",
                    "description": "Vendor name to send reminder to"
                },
                "invoice_id": {
                    "type": "string",
                    "description": "Optional specific invoice ID"
                }
            },
            "required": ["vendor_name"]
        }
    },
]

ADMIN_TOOLS = [
    {
        "name": "schedule_meeting",
        "description": "Schedule a new meeting",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Meeting title"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM format"},
                "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses"
                },
                "description": {"type": "string", "description": "Meeting description"}
            },
            "required": ["title", "date", "time"]
        }
    },
    {
        "name": "list_meetings",
        "description": "List upcoming meetings",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Filter by date in YYYY-MM-DD format, or 'upcoming' for future meetings"
                }
            },
            "required": ["date"]
        }
    },
    {
        "name": "register_visitor",
        "description": "Register a visitor for pre-approval",
        "parameters": {
            "type": "object",
            "properties": {
                "visitor_name": {"type": "string", "description": "Visitor's full name"},
                "company": {"type": "string", "description": "Visitor's company"},
                "email": {"type": "string", "description": "Visitor's email"},
                "phone": {"type": "string", "description": "Visitor's phone number"},
                "purpose": {"type": "string", "description": "Purpose of visit"}
            },
            "required": ["visitor_name", "purpose"]
        }
    },
    {
        "name": "list_assets",
        "description": "List assets filtered by status or type",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["available", "assigned", "maintenance", "retired", "all"],
                    "description": "Filter by asset status"
                },
                "asset_type": {
                    "type": "string",
                    "description": "Filter by asset type (laptop, monitor, desk, etc.)"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "add_asset",
        "description": "Add a new asset to the inventory",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Asset name"},
                "asset_type": {"type": "string", "description": "Type of asset"},
                "serial_number": {"type": "string", "description": "Serial number"},
                "location": {"type": "string", "description": "Physical location"}
            },
            "required": ["name", "asset_type"]
        }
    },
    {
        "name": "request_supply",
        "description": "Request office supplies",
        "parameters": {
            "type": "object",
            "properties": {
                "supply_name": {"type": "string", "description": "Name of the supply item"},
                "quantity": {"type": "integer", "description": "Quantity needed"},
                "reason": {"type": "string", "description": "Reason for request"}
            },
            "required": ["supply_name", "quantity"]
        }
    },
    {
        "name": "check_inventory",
        "description": "Check office supply inventory levels",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter"
                },
                "show_low_stock_only": {
                    "type": "boolean",
                    "description": "Show only items below minimum quantity"
                }
            },
            "required": []
        }
    },
    {
        "name": "create_ticket",
        "description": "Create a support or service ticket",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Ticket title"},
                "description": {"type": "string", "description": "Detailed description"},
                "category": {
                    "type": "string",
                    "enum": ["it", "facilities", "hr", "general"],
                    "description": "Ticket category"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level"
                }
            },
            "required": ["title", "description"]
        }
    },
    {
        "name": "list_tickets",
        "description": "List tickets for the current user",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "resolved", "closed", "all"],
                    "description": "Filter by status"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "post_announcement",
        "description": "Post a company announcement",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Announcement title"},
                "content": {"type": "string", "description": "Announcement content"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Priority level"
                }
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "get_announcements",
        "description": "Get recent company announcements",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent announcements to fetch"
                }
            },
            "required": []
        }
    },
]

HR_TOOLS_EXTRA = [
    {
        "name": "onboard_employee",
        "description": "Onboard a new employee - create their employee record and account",
        "parameters": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string", "description": "Employee's full name"},
                "email": {"type": "string", "description": "Employee's email address"},
                "department": {"type": "string", "description": "Department name"},
                "role": {"type": "string", "description": "Job role/title"},
                "manager_email": {"type": "string", "description": "Manager's email address"},
                "employee_id": {"type": "string", "description": "Optional employee ID"}
            },
            "required": ["full_name", "email", "department"]
        }
    },
    {
        "name": "generate_hr_report",
        "description": "Generate an HR report summarizing employee data, leave usage, attendance",
        "parameters": {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["employee_summary", "leave_usage", "attendance_summary", "headcount"],
                    "description": "Type of HR report"
                },
                "month": {
                    "type": "string",
                    "description": "Month in YYYY-MM format, defaults to current month"
                }
            },
            "required": ["report_type"]
        }
    },
    {
        "name": "list_employee_documents",
        "description": "List employee-related documents indexed in the system (contracts, NDAs, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_name": {
                    "type": "string",
                    "description": "Filter by employee name"
                },
                "document_type": {
                    "type": "string",
                    "description": "Type of document (contract, payslip, policy, etc.)"
                }
            },
            "required": []
        }
    },
]

ACCOUNTING_TOOLS_EXTRA = [
    {
        "name": "track_payments",
        "description": "Track payment status for invoices. Shows all payments and their status.",
        "parameters": {
            "type": "object",
            "properties": {
                "vendor_name": {
                    "type": "string",
                    "description": "Filter by vendor name"
                },
                "status": {
                    "type": "string",
                    "enum": ["paid", "pending", "overdue", "all"],
                    "description": "Payment status filter"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "reconcile_vendor_statement",
        "description": "Reconcile a vendor statement against recorded invoices to find discrepancies",
        "parameters": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string", "description": "Vendor name"},
                "statement_file_id": {
                    "type": "string",
                    "description": "File ID of uploaded vendor statement PDF"
                }
            },
            "required": ["vendor_name"]
        }
    },
    {
        "name": "create_accounting_entry",
        "description": "Create a double-entry accounting entry (debit/credit)",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_date": {"type": "string", "description": "Entry date in YYYY-MM-DD format"},
                "account_code": {"type": "string", "description": "Account code (e.g. 1100 for Cash)"},
                "account_name": {"type": "string", "description": "Account name"},
                "debit_amount": {"type": "number", "description": "Debit amount (0 if credit entry)"},
                "credit_amount": {"type": "number", "description": "Credit amount (0 if debit entry)"},
                "description": {"type": "string", "description": "Entry description"}
            },
            "required": ["entry_date", "account_code", "account_name", "description"]
        }
    },
    {
        "name": "add_to_audit_storage",
        "description": "Store a document in audit-ready storage with metadata tags",
        "parameters": {
            "type": "object",
            "properties": {
                "document_name": {"type": "string", "description": "Document name"},
                "file_id": {"type": "string", "description": "File ID of the uploaded document"},
                "category": {"type": "string", "description": "Document category (invoice, receipt, report, contract)"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search tags for the document"
                },
                "notes": {"type": "string", "description": "Optional notes"}
            },
            "required": ["document_name", "category"]
        }
    },
]

ADMIN_TOOLS_EXTRA = [
    {
        "name": "file_document",
        "description": "File and categorize a document for easy retrieval later",
        "parameters": {
            "type": "object",
            "properties": {
                "document_name": {"type": "string", "description": "Document name"},
                "file_id": {"type": "string", "description": "File ID of the uploaded document"},
                "category": {
                    "type": "string",
                    "enum": ["contract", "report", "policy", "invoice", "misc"],
                    "description": "Document category"
                },
                "department": {
                    "type": "string",
                    "description": "Department this document belongs to"
                }
            },
            "required": ["document_name", "category"]
        }
    },
    {
        "name": "generate_admin_report",
        "description": "Generate an administrative report summarizing assets, tickets, supplies, and meetings",
        "parameters": {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["assets_summary", "tickets_summary", "supplies_summary", "meetings_summary", "overall"],
                    "description": "Type of admin report"
                }
            },
            "required": ["report_type"]
        }
    },
]

ALL_TOOLS = HR_TOOLS + HR_TOOLS_EXTRA + ACCOUNTING_TOOLS + ACCOUNTING_TOOLS_EXTRA + ADMIN_TOOLS + ADMIN_TOOLS_EXTRA
TOOL_NAME_MAP = {t["name"]: t for t in ALL_TOOLS}
