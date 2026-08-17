import json
import os
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import (
    LeaveRequest, AttendanceLog, Invoice, Expense, Meeting, Asset,
    Ticket, ApprovalRequest, Notification, OfficeSupply, SupplyRequest,
    Visitor, CompanyAnnouncement, User, AccountingEntry, AuditDocument,
    HRPolicy, Document,
)
from app.services.groq_service import generate_answer
from app.services.rag import get_store, get_registry, _user_key
from app.config import RAGConfig


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _now_str():
    return datetime.now().strftime("%H:%M")


def _get_user_email_from_session():
    from flask import session
    return session.get("user", "")


def _db_session():
    return SessionLocal()


def execute_tool(name: str, args: dict, user_email: str = None) -> dict:
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        return {"error": f"Unknown tool: {name}"}
    try:
        result = executor(args, user_email or _get_user_email_from_session())
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _apply_leave(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        leave = LeaveRequest(
            user_email=user_email,
            leave_type=args["leave_type"],
            start_date=args["start_date"],
            end_date=args["end_date"],
            reason=args.get("reason", ""),
        )
        db.add(leave)

        user = db.query(User).filter(User.email == user_email).first()
        manager_email = user.manager_email if user else ""

        approval = ApprovalRequest(
            workflow_type="leave",
            requester=user_email,
            approver=manager_email or "admin@ceap.school",
            metadata_json={
                "leave_id": leave.id,
                "leave_type": args["leave_type"],
                "start_date": args["start_date"],
                "end_date": args["end_date"],
            },
            steps_json=[
                {"order": 1, "role": "manager", "status": "pending"}
            ],
        )
        db.add(approval)
        db.commit()

        return {
            "leave_id": leave.id,
            "status": "pending",
            "message": f"Leave request submitted for {args['leave_type']} leave from {args['start_date']} to {args['end_date']}. Sent for approval.",
        }
    finally:
        db.close()


def _get_leave_balance(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        balance = json.loads(user.leave_balance_json) if user and user.leave_balance_json else {}
        leave_type = args.get("leave_type", "all")
        if leave_type == "all":
            return {"balance": balance, "message": "Leave balances retrieved"}
        days = balance.get(leave_type, 0)
        return {"balance": {leave_type: days}, "message": f"You have {days} {leave_type} days remaining"}
    finally:
        db.close()


def _list_my_leaves(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(LeaveRequest).filter(LeaveRequest.user_email == user_email)
        status_filter = args.get("status", "all")
        if status_filter != "all":
            query = query.filter(LeaveRequest.status == status_filter)
        leaves = query.order_by(LeaveRequest.created_at.desc()).limit(20).all()
        return {
            "leaves": [
                {
                    "id": l.id,
                    "type": l.leave_type,
                    "start": l.start_date,
                    "end": l.end_date,
                    "status": l.status,
                    "reason": l.reason,
                }
                for l in leaves
            ],
            "count": len(leaves),
        }
    finally:
        db.close()


def _get_attendance(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        start = args["start_date"]
        end = args["end_date"]
        records = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.user_email == user_email,
                AttendanceLog.date >= start,
                AttendanceLog.date <= end,
            )
            .order_by(AttendanceLog.date.desc())
            .all()
        )
        return {
            "records": [
                {
                    "date": r.date,
                    "check_in": r.check_in,
                    "check_out": r.check_out,
                    "source": r.source,
                }
                for r in records
            ],
            "count": len(records),
        }
    finally:
        db.close()


def _mark_attendance(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        today = _today_str()
        action = args["action"]
        timestamp = args.get("timestamp", _now_str())

        existing = (
            db.query(AttendanceLog)
            .filter(AttendanceLog.user_email == user_email, AttendanceLog.date == today)
            .first()
        )

        if action == "check_in":
            if existing:
                return {"message": f"Already checked in at {existing.check_in} today"}
            log = AttendanceLog(user_email=user_email, date=today, check_in=timestamp, check_out="")
            db.add(log)
        else:
            if not existing:
                return {"message": "No check-in record found for today"}
            existing.check_out = timestamp

        db.commit()
        return {"message": f"{action.replace('_', ' ').title()} recorded at {timestamp}"}
    finally:
        db.close()


def _get_payslip(args: dict, user_email: str) -> dict:
    period = args.get("period", datetime.now().strftime("%Y-%m"))
    user_key = _user_key()
    store = get_store()
    query = f"payslip {period} {user_email.split('@')[0]}"
    try:
        chunks = store.search(query, top_k=RAGConfig.TOP_K)
        if chunks:
            return {
                "found": True,
                "period": period,
                "results": [
                    {"source": c.get("source", ""), "excerpt": c.get("text", "")[:300]}
                    for c in chunks[:3]
                ],
                "message": f"Found payslip documents for {period}. Searched your indexed documents."
            }
        return {"found": False, "period": period, "message": "No payslip found for this period. Upload your payslip PDF and try again."}
    except Exception:
        return {"found": False, "period": period, "message": "Please upload your payslip PDF documents first, then search again."}


def _hr_policy_file_ids(user_key: str, store) -> list | None:
    """File IDs for HR/leave policy documents; None means search all indexed docs."""
    db = _db_session()
    try:
        rows = (
            db.query(Document.file_id)
            .filter(Document.user_key == user_key)
            .filter(
                (Document.department == "hr")
                | Document.name.ilike("%policy%")
                | Document.name.ilike("%leave%")
            )
            .all()
        )
        indexed = store.indexed_file_ids()
        file_ids = [r[0] for r in rows if r[0] in indexed]
        return file_ids if file_ids else None
    finally:
        db.close()


def _search_hr_policy(args: dict, user_email: str) -> dict:
    query = args["query"]
    user_key = _user_key()
    store = get_store()

    policy_sections = []
    db = _db_session()
    try:
        policies = (
            db.query(HRPolicy)
            .filter(HRPolicy.user_key == user_key, HRPolicy.active == 1)
            .order_by(HRPolicy.updated_at.desc())
            .all()
        )
        for policy in policies:
            rules = policy.rules_json or {}
            routing = rules.get("approver_routing")
            extra = f"\nApprover routing: {routing}" if routing else ""
            policy_sections.append(
                f"--- {policy.name} ({policy.category}) ---\n{policy.content}{extra}"
            )
    finally:
        db.close()

    try:
        source_filter = _hr_policy_file_ids(user_key, store)
        chunks = store.search(query, top_k=RAGConfig.TOP_K, source_filter=source_filter)
        doc_texts = "\n\n".join(f"{c['text']}" for c in chunks[:3]) if chunks else ""
        if policy_sections:
            doc_texts = "\n\n".join(policy_sections) + (
                f"\n\n{doc_texts}" if doc_texts else ""
            )

        if doc_texts:
            answer = generate_answer(
                "You are an HR policy expert. Answer the following question using ONLY "
                "the provided policy documents:\n\n"
                f"POLICY DOCUMENTS:\n{doc_texts}\n\n"
                f"QUESTION: {query}\n\n"
                "Provide a concise answer with reference to the specific policy."
            )
            sources = [c.get("source", "") for c in chunks[:3]] if chunks else []
            if policies:
                sources = [p.name for p in policies] + sources
            return {
                "found": True,
                "answer": answer or doc_texts[:500],
                "sources": sources,
            }
        return {"found": False, "message": "No HR policy documents found. Upload your policy documents first."}
    except Exception as e:
        return {"found": False, "message": f"Error searching policies: {str(e)}"}


def _get_employee_info(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return {"message": "Employee not found"}
        return {
            "email": user.email,
            "role": user.role,
            "department": user.department,
            "employee_id": user.employee_id,
            "manager": user.manager_email,
            "leave_balance": json.loads(user.leave_balance_json) if user.leave_balance_json else {},
        }
    finally:
        db.close()


def _get_pending_approvals(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        role = args.get("role", "approver")
        if role == "approver":
            requests = (
                db.query(ApprovalRequest)
                .filter(ApprovalRequest.approver == user_email, ApprovalRequest.status == "pending")
                .order_by(ApprovalRequest.created_at.desc())
                .all()
            )
        else:
            requests = (
                db.query(ApprovalRequest)
                .filter(ApprovalRequest.requester == user_email)
                .order_by(ApprovalRequest.created_at.desc())
                .all()
            )
        return {
            "requests": [
                {
                    "id": r.id,
                    "type": r.workflow_type,
                    "requester": r.requester,
                    "approver": r.approver,
                    "status": r.status,
                    "details": r.metadata_json,
                    "created": r.created_at,
                }
                for r in requests
            ],
            "count": len(requests),
        }
    finally:
        db.close()


def _approve_or_reject_request(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == args["request_id"]).first()
        if not req:
            return {"message": "Approval request not found"}
        if req.approver != user_email:
            return {"message": "You are not the approver for this request"}

        req.status = args["decision"]
        req.updated_at = time.time()
        db.commit()

        if req.workflow_type == "leave":
            leave_id = req.metadata_json.get("leave_id")
            if leave_id:
                leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
                if leave:
                    leave.status = args["decision"]
                    if args["decision"] == "approved":
                        leave.approved_by = user_email
                    db.commit()

        notif = Notification(
            user_email=req.requester,
            type="approval",
            title=f"Leave {args['decision']}",
            message=f"Your leave request has been {args['decision']} by {user_email}.",
        )
        db.add(notif)
        db.commit()

        return {"message": f"Request {args['decision']} successfully", "request_id": req.id}
    finally:
        db.close()


def _create_invoice(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        inv = Invoice(
            user_key=_user_key(),
            invoice_number=args["invoice_number"],
            vendor_name=args["vendor_name"],
            date=args["date"],
            due_date=args.get("due_date", ""),
            total_amount=args["total_amount"],
            tax=args.get("tax", 0.0),
            currency=args.get("currency", "USD"),
            status="pending",
        )
        db.add(inv)
        db.commit()
        return {
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "message": f"Invoice {inv.invoice_number} created successfully",
        }
    finally:
        db.close()


def _extract_invoice_data(args: dict, user_email: str) -> dict:
    file_id = args["file_id"]
    user_key = _user_key()
    store = get_store()

    try:
        chunks = store.search(f"invoice {file_id}", top_k=5, source_filter=[file_id] if file_id else None)
        if not chunks:
            text = ""
        else:
            text = "\n".join(c.get("text", "") for c in chunks)

        if not text:
            return {"message": "Could not retrieve text from the file. Make sure it's a readable PDF."}

        prompt = (
            "Extract the following fields from this invoice text. Return ONLY valid JSON.\n"
            "Fields: invoice_number, vendor_name, date, due_date, total_amount, tax, currency, line_items (array of {description, amount})\n\n"
            f"INVOICE TEXT:\n{text[:4000]}\n\nJSON:"
        )
        extracted = generate_answer(prompt)
        parsed = {}
        if extracted:
            cleaned = extracted.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0]
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                parsed = {"raw": cleaned}

        db = _db_session()
        try:
            inv = Invoice(
                user_key=user_key,
                invoice_number=parsed.get("invoice_number", ""),
                vendor_name=parsed.get("vendor_name", ""),
                date=parsed.get("date", ""),
                due_date=parsed.get("due_date", ""),
                total_amount=float(parsed.get("total_amount", 0)),
                tax=float(parsed.get("tax", 0)),
                currency=parsed.get("currency", "USD"),
                status="pending",
                file_ref=file_id,
                extracted_data=parsed,
            )
            db.add(inv)
            db.commit()
            parsed["invoice_id"] = inv.id
        finally:
            db.close()

        return {
            "extracted": parsed,
            "message": "Invoice data extracted and saved. Please review and verify the information.",
        }
    except Exception as e:
        return {"message": f"Error extracting invoice data: {str(e)}"}


def _list_invoices(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(Invoice).filter(Invoice.user_key == _user_key())
        status = args.get("status", "all")
        if status != "all":
            query = query.filter(Invoice.status == status)
        invoices = query.order_by(Invoice.created_at.desc()).limit(50).all()
        return {
            "invoices": [
                {
                    "id": inv.id,
                    "number": inv.invoice_number,
                    "vendor": inv.vendor_name,
                    "date": inv.date,
                    "total": inv.total_amount,
                    "status": inv.status,
                    "currency": inv.currency,
                }
                for inv in invoices
            ],
            "count": len(invoices),
        }
    finally:
        db.close()


def _mark_invoice_paid(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        inv = db.query(Invoice).filter(Invoice.id == args["invoice_id"]).first()
        if not inv:
            return {"message": "Invoice not found"}
        inv.status = "paid"
        db.commit()
        return {"message": f"Invoice {inv.invoice_number} marked as paid on {args.get('payment_date', 'today')}"}
    finally:
        db.close()


def _submit_expense(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        expense = Expense(
            user_email=user_email,
            category=args["category"],
            amount=args["amount"],
            description=args.get("description", ""),
            receipt_file=args.get("receipt_file_id", ""),
        )
        db.add(expense)

        user = db.query(User).filter(User.email == user_email).first()
        manager = user.manager_email if user else ""

        approval = ApprovalRequest(
            workflow_type="expense",
            requester=user_email,
            approver=manager or "admin@ceap.school",
            metadata_json={
                "expense_id": expense.id,
                "category": args["category"],
                "amount": args["amount"],
            },
            steps_json=[{"order": 1, "role": "manager", "status": "pending"}],
        )
        db.add(approval)
        db.commit()
        return {
            "expense_id": expense.id,
            "message": f"Expense claim for ${args['amount']} submitted for approval.",
        }
    finally:
        db.close()


def _list_expenses(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(Expense).filter(Expense.user_email == user_email)
        status = args.get("status", "all")
        if status != "all":
            query = query.filter(Expense.status == status)
        expenses = query.order_by(Expense.created_at.desc()).limit(50).all()
        return {
            "expenses": [
                {
                    "id": e.id,
                    "category": e.category,
                    "amount": e.amount,
                    "description": e.description,
                    "status": e.status,
                }
                for e in expenses
            ],
            "count": len(expenses),
        }
    finally:
        db.close()


def _get_financial_summary(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        month = args.get("month", datetime.now().strftime("%Y-%m"))
        invoices = db.query(Invoice).filter(Invoice.user_key == _user_key()).all()
        total_invoiced = sum(i.total_amount for i in invoices)
        total_paid = sum(i.total_amount for i in invoices if i.status == "paid")
        total_pending = sum(i.total_amount for i in invoices if i.status == "pending")

        expenses_data = db.query(Expense).all()
        total_expenses = sum(e.amount for e in expenses_data)

        return {
            "month": month,
            "summary": {
                "total_invoiced": round(total_invoiced, 2),
                "total_paid": round(total_paid, 2),
                "total_pending": round(total_pending, 2),
                "total_expenses": round(total_expenses, 2),
                "net": round(total_invoiced - total_expenses, 2),
                "invoice_count": len(invoices),
                "expense_count": len(expenses_data),
            },
        }
    finally:
        db.close()


def _send_payment_reminder(args: dict, user_email: str) -> dict:
    vendor = args["vendor_name"]
    db = _db_session()
    try:
        overdue = (
            db.query(Invoice)
            .filter(Invoice.vendor_name.ilike(f"%{vendor}%"), Invoice.status == "pending")
            .all()
        )
        if not overdue:
            return {"message": f"No pending invoices found for {vendor}"}

        total = sum(i.total_amount for i in overdue)
        return {
            "message": f"Payment reminder ready for {vendor} ({len(overdue)} invoices, total ${total:.2f}). "
                       f"Notification sent to your notification inbox.",
            "invoices": [{"id": i.id, "number": i.invoice_number, "amount": i.total_amount} for i in overdue],
        }
    finally:
        db.close()


def _schedule_meeting(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        meeting = Meeting(
            title=args["title"],
            date=args["date"],
            time=args.get("time", "09:00"),
            duration_minutes=args.get("duration_minutes", 60),
            attendees=args.get("attendees", []),
            description=args.get("description", ""),
            organizer=user_email,
        )
        db.add(meeting)

        for attendee in meeting.attendees:
            notif = Notification(
                user_email=attendee,
                type="meeting",
                title=f"Meeting: {meeting.title}",
                message=f"You're invited to '{meeting.title}' on {meeting.date} at {meeting.time}",
            )
            db.add(notif)

        db.commit()
        return {
            "meeting_id": meeting.id,
            "message": f"Meeting '{meeting.title}' scheduled for {meeting.date} at {meeting.time}",
        }
    finally:
        db.close()


def _list_meetings(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(Meeting)
        date_filter = args.get("date", "upcoming")
        if date_filter == "upcoming":
            query = query.filter(Meeting.date >= _today_str())
        else:
            query = query.filter(Meeting.date == date_filter)
        meetings = query.order_by(Meeting.date.asc(), Meeting.time.asc()).limit(20).all()
        return {
            "meetings": [
                {
                    "id": m.id,
                    "title": m.title,
                    "date": m.date,
                    "time": m.time,
                    "duration": m.duration_minutes,
                    "attendees": m.attendees,
                    "organizer": m.organizer,
                    "status": m.status,
                }
                for m in meetings
            ],
            "count": len(meetings),
        }
    finally:
        db.close()


def _register_visitor(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        visitor = Visitor(
            name=args["visitor_name"],
            company=args.get("company", ""),
            email=args.get("email", ""),
            phone=args.get("phone", ""),
            host_email=user_email,
            purpose=args.get("purpose", ""),
        )
        db.add(visitor)
        db.commit()
        return {
            "visitor_id": visitor.id,
            "message": f"Visitor '{args['visitor_name']}' registered. They'll be guided upon arrival.",
        }
    finally:
        db.close()


def _list_assets(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(Asset)
        status = args.get("status", "all")
        if status != "all":
            query = query.filter(Asset.status == status)
        asset_type = args.get("asset_type", "")
        if asset_type:
            query = query.filter(Asset.asset_type.ilike(f"%{asset_type}%"))
        assets = query.order_by(Asset.name.asc()).limit(50).all()
        return {
            "assets": [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.asset_type,
                    "serial": a.serial_number,
                    "assigned_to": a.assigned_to,
                    "location": a.location,
                    "status": a.status,
                }
                for a in assets
            ],
            "count": len(assets),
        }
    finally:
        db.close()


def _add_asset(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        asset = Asset(
            name=args["name"],
            asset_type=args.get("asset_type", ""),
            serial_number=args.get("serial_number", ""),
            location=args.get("location", ""),
        )
        db.add(asset)
        db.commit()
        return {"asset_id": asset.id, "message": f"Asset '{args['name']}' added to inventory"}
    finally:
        db.close()


def _request_supply(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        req = SupplyRequest(
            user_email=user_email,
            supply_name=args["supply_name"],
            quantity=args["quantity"],
            reason=args.get("reason", ""),
        )
        db.add(req)
        db.commit()
        return {
            "request_id": req.id,
            "message": f"Request for {args['quantity']} x '{args['supply_name']}' submitted.",
        }
    finally:
        db.close()


def _check_inventory(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(OfficeSupply)
        category = args.get("category", "")
        if category:
            query = query.filter(OfficeSupply.category == category)
        supplies = query.order_by(OfficeSupply.name.asc()).all()

        if args.get("show_low_stock_only"):
            supplies = [s for s in supplies if s.quantity <= s.min_quantity]

        return {
            "supplies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "quantity": s.quantity,
                    "min_quantity": s.min_quantity,
                    "unit": s.unit,
                    "location": s.location,
                    "low_stock": s.quantity <= s.min_quantity,
                }
                for s in supplies
            ],
            "count": len(supplies),
        }
    finally:
        db.close()


def _create_ticket(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        ticket = Ticket(
            title=args["title"],
            description=args.get("description", ""),
            category=args.get("category", "general"),
            priority=args.get("priority", "medium"),
            created_by=user_email,
        )
        db.add(ticket)
        db.commit()
        return {
            "ticket_id": ticket.id,
            "message": f"Ticket '{args['title']}' created with {ticket.priority} priority.",
        }
    finally:
        db.close()


def _list_tickets(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(Ticket).filter(
            (Ticket.created_by == user_email) | (Ticket.assignee == user_email)
        )
        status = args.get("status", "all")
        if status != "all":
            query = query.filter(Ticket.status == status)
        tickets = query.order_by(Ticket.updated_at.desc()).limit(50).all()
        return {
            "tickets": [
                {
                    "id": t.id,
                    "title": t.title,
                    "category": t.category,
                    "priority": t.priority,
                    "status": t.status,
                    "assignee": t.assignee,
                }
                for t in tickets
            ],
            "count": len(tickets),
        }
    finally:
        db.close()


def _post_announcement(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        announcement = CompanyAnnouncement(
            title=args["title"],
            content=args["content"],
            priority=args.get("priority", "normal"),
            created_by=user_email,
        )
        db.add(announcement)

        all_users = db.query(User.email).all()
        for (email,) in all_users:
            if email != user_email:
                notif = Notification(
                    user_email=email,
                    type="announcement",
                    title=args["title"],
                    message=args["content"][:200],
                )
                db.add(notif)

        db.commit()
        return {"announcement_id": announcement.id, "message": "Announcement posted to all users"}
    finally:
        db.close()


def _get_announcements(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        limit = args.get("limit", 10)
        announcements = (
            db.query(CompanyAnnouncement)
            .order_by(CompanyAnnouncement.created_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "announcements": [
                {
                    "id": a.id,
                    "title": a.title,
                    "content": a.content[:500],
                    "priority": a.priority,
                    "created_by": a.created_by,
                    "created_at": a.created_at,
                }
                for a in announcements
            ],
            "count": len(announcements),
        }
    finally:
        db.close()


def _onboard_employee(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        full_name = args["full_name"]
        email = args["email"]
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"message": f"Employee with email {email} already exists"}
        import werkzeug.security
        temp_password = werkzeug.security.generate_password_hash("changeme123")
        employee_id = args.get("employee_id", f"EMP{int(time.time())}")
        user = User(
            email=email,
            full_name=full_name,
            password_hash=temp_password,
            role="user",
            department=args.get("department", ""),
            employee_id=employee_id,
            manager_email=args.get("manager_email", ""),
        )
        db.add(user)
        notif = Notification(
            user_email=args.get("manager_email", user_email),
            type="onboarding",
            title=f"New employee: {full_name}",
            message=f"{full_name} ({email}) has been onboarded in {args.get('department', '')} department.",
        )
        db.add(notif)
        db.commit()
        return {
            "employee_id": employee_id,
            "message": f"Employee {full_name} onboarded successfully. Temporary password set to 'changeme123'.",
        }
    finally:
        db.close()


def _generate_hr_report(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        report_type = args["report_type"]
        month = args.get("month", datetime.now().strftime("%Y-%m"))
        if report_type == "employee_summary":
            users = db.query(User).all()
            return {
                "report_type": report_type,
                "data": {
                    "total_employees": len(users),
                    "departments": list(set(u.department for u in users if u.department)),
                    "employees": [{"email": u.email, "name": u.full_name, "department": u.department, "role": u.role} for u in users],
                },
                "message": f"Employee summary generated: {len(users)} total employees",
            }
        elif report_type == "leave_usage":
            leaves = db.query(LeaveRequest).all()
            usage = {}
            for l in leaves:
                usage[l.leave_type] = usage.get(l.leave_type, 0) + 1
            return {
                "report_type": report_type,
                "data": {"month": month, "leave_usage": usage, "total_requests": len(leaves)},
                "message": f"Leave usage report for {month}: {len(leaves)} requests",
            }
        elif report_type == "attendance_summary":
            logs = db.query(AttendanceLog).filter(AttendanceLog.date.like(f"{month}-%")).all()
            return {
                "report_type": report_type,
                "data": {"month": month, "total_records": len(logs)},
                "message": f"Attendance summary for {month}: {len(logs)} records",
            }
        elif report_type == "headcount":
            users = db.query(User).all()
            dept_count = {}
            for u in users:
                d = u.department or "Unassigned"
                dept_count[d] = dept_count.get(d, 0) + 1
            return {
                "report_type": report_type,
                "data": {"total": len(users), "by_department": dept_count},
                "message": f"Headcount report: {len(users)} employees across {len(dept_count)} departments",
            }
    finally:
        db.close()


def _list_employee_documents(args: dict, user_email: str) -> dict:
    store = get_store()
    try:
        query_parts = ["employee", "contract", "document"]
        if args.get("employee_name"):
            query_parts.append(args["employee_name"])
        if args.get("document_type"):
            query_parts.append(args["document_type"])
        query = " ".join(query_parts)
        chunks = store.search(query, top_k=RAGConfig.TOP_K)
        if chunks:
            return {
                "found": True,
                "documents": [{"name": c.get("source", ""), "excerpt": c.get("text", "")[:200]} for c in chunks[:5]],
                "message": f"Found {len(chunks[:5])} employee documents matching your criteria",
            }
        return {"found": False, "message": "No employee documents found. Upload them first."}
    except Exception:
        return {"found": False, "message": "Upload employee documents (contracts, NDAs, etc.) then search again."}


def _track_payments(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        query = db.query(Invoice).filter(Invoice.user_key == _user_key())
        status = args.get("status", "all")
        if status != "all":
            query = query.filter(Invoice.status == status)
        vendor = args.get("vendor_name", "")
        if vendor:
            query = query.filter(Invoice.vendor_name.ilike(f"%{vendor}%"))
        invoices = query.order_by(Invoice.created_at.desc()).limit(50).all()
        total = sum(i.total_amount for i in invoices)
        return {
            "payments": [
                {"number": i.invoice_number, "vendor": i.vendor_name, "amount": i.total_amount, "status": i.status, "date": i.date, "due": i.due_date}
                for i in invoices
            ],
            "total_amount": round(total, 2),
            "count": len(invoices),
            "message": f"Found {len(invoices)} invoices totaling ${total:.2f}",
        }
    finally:
        db.close()


def _reconcile_vendor_statement(args: dict, user_email: str) -> dict:
    vendor = args["vendor_name"]
    db = _db_session()
    try:
        invoices = db.query(Invoice).filter(Invoice.vendor_name.ilike(f"%{vendor}%")).all()
        if not invoices:
            return {"message": f"No invoices found for vendor '{vendor}'"}
        total_invoiced = sum(i.total_amount for i in invoices)
        total_paid = sum(i.total_amount for i in invoices if i.status == "paid")
        total_pending = sum(i.total_amount for i in invoices if i.status == "pending")
        return {
            "vendor": vendor,
            "reconciliation": {
                "total_invoiced": round(total_invoiced, 2),
                "total_paid": round(total_paid, 2),
                "total_pending": round(total_pending, 2),
                "balance_due": round(total_invoiced - total_paid, 2),
                "invoice_count": len(invoices),
                "paid_count": sum(1 for i in invoices if i.status == "paid"),
                "pending_count": sum(1 for i in invoices if i.status == "pending"),
                "invoices": [{"number": i.invoice_number, "amount": i.total_amount, "status": i.status} for i in invoices],
            },
            "message": f"Reconciliation for {vendor}: ${total_invoiced:.2f} invoiced, ${total_paid:.2f} paid, ${total_invoiced - total_paid:.2f} outstanding",
        }
    finally:
        db.close()


def _create_accounting_entry(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        entry = AccountingEntry(
            user_key=_user_key(),
            entry_date=args["entry_date"],
            account_code=args["account_code"],
            account_name=args["account_name"],
            description=args.get("description", ""),
            debit_amount=args.get("debit_amount", 0.0),
            credit_amount=args.get("credit_amount", 0.0),
            created_by=user_email,
        )
        db.add(entry)
        db.commit()
        return {
            "entry_id": entry.id,
            "message": f"Accounting entry created: {args['account_name']} (${args.get('debit_amount', 0):.2f} debit / ${args.get('credit_amount', 0):.2f} credit)",
        }
    finally:
        db.close()


def _add_to_audit_storage(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        doc = AuditDocument(
            user_key=_user_key(),
            document_name=args["document_name"],
            file_ref=args.get("file_id", ""),
            category=args["category"],
            tags=args.get("tags", []),
            notes=args.get("notes", ""),
            uploaded_by=user_email,
        )
        db.add(doc)
        db.commit()
        return {
            "document_id": doc.id,
            "message": f"'{args['document_name']}' stored in audit-ready archive (category: {args['category']})",
        }
    finally:
        db.close()


def _file_document(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        doc = AuditDocument(
            user_key=_user_key(),
            document_name=args["document_name"],
            file_ref=args.get("file_id", ""),
            category=args["category"],
            tags=[args.get("department", "general")],
            notes=f"Filed by {user_email}",
            uploaded_by=user_email,
        )
        db.add(doc)
        db.commit()
        return {
            "document_id": doc.id,
            "message": f"'{args['document_name']}' filed under {args['category']} for {args.get('department', 'general')} department",
        }
    finally:
        db.close()


def _generate_admin_report(args: dict, user_email: str) -> dict:
    db = _db_session()
    try:
        report_type = args["report_type"]
        if report_type == "assets_summary":
            assets = db.query(Asset).all()
            status_count = {}
            for a in assets:
                s = a.status or "unknown"
                status_count[s] = status_count.get(s, 0) + 1
            return {"report_type": report_type, "data": {"total": len(assets), "by_status": status_count}, "message": f"{len(assets)} assets in inventory"}
        elif report_type == "tickets_summary":
            tickets = db.query(Ticket).all()
            status_count = {}
            for t in tickets:
                status_count[t.status] = status_count.get(t.status, 0) + 1
            return {"report_type": report_type, "data": {"total": len(tickets), "by_status": status_count}, "message": f"{len(tickets)} tickets in system"}
        elif report_type == "supplies_summary":
            supplies = db.query(OfficeSupply).all()
            low_stock = [s for s in supplies if s.quantity <= s.min_quantity]
            return {"report_type": report_type, "data": {"total_items": len(supplies), "low_stock_count": len(low_stock), "low_stock_items": [s.name for s in low_stock]}, "message": f"{len(supplies)} supply items, {len(low_stock)} below minimum"}
        elif report_type == "meetings_summary":
            meetings = db.query(Meeting).filter(Meeting.date >= _today_str()).all()
            return {"report_type": report_type, "data": {"upcoming": len(meetings)}, "message": f"{len(meetings)} upcoming meetings scheduled"}
        elif report_type == "overall":
            assets = db.query(Asset).count()
            tickets = db.query(Ticket).count()
            supplies = db.query(OfficeSupply).count()
            meetings = db.query(Meeting).filter(Meeting.date >= _today_str()).count()
            return {"report_type": report_type, "data": {"assets": assets, "tickets": tickets, "supplies": supplies, "upcoming_meetings": meetings}, "message": f"Overall admin summary: {assets} assets, {tickets} tickets, {supplies} supply items, {meetings} upcoming meetings"}
    finally:
        db.close()


def _generate_circular_draft(args: dict, user_email: str) -> dict:
    topic = args.get("topic", "")
    audience = args.get("audience", "")
    key_points = args.get("key_points", "")
    prompt = (
        f"Draft a school circular about '{topic}' for {audience}.\n"
        f"Key points to include: {key_points}\n\n"
        "Format: [School Name], [Date], subject line, body with clear sections, closing with principal's name."
    )
    try:
        from app.services.groq_service import generate_answer
        draft = generate_answer(prompt)
        return {
            "draft": draft or f"Circular draft about {topic} for {audience}",
            "topic": topic,
            "audience": audience,
            "message": f"Circular draft generated for: {topic}",
        }
    except Exception as e:
        return {"draft": "", "message": f"Could not generate circular: {str(e)}"}


def _search_school_policy(args: dict, user_email: str) -> dict:
    query = args["query"]
    from app.services.rag import get_store
    from app.config import RAGConfig
    store = get_store()
    try:
        chunks = store.search(query, top_k=RAGConfig.TOP_K)
        if chunks:
            texts = "\n\n".join(f"{c['text']}" for c in chunks[:3])
            from app.services.groq_service import generate_answer
            answer = generate_answer(
                f"You are a school policy expert. Answer using ONLY the provided policy documents:\n\n"
                f"POLICY DOCUMENTS:\n{texts}\n\n"
                f"QUESTION: {query}\n\n"
                f"Provide a concise answer with reference to the specific policy."
            )
            return {
                "found": True,
                "answer": answer or texts[:500],
                "sources": [c.get("source", "") for c in chunks[:3]],
            }
        return {"found": False, "message": "No school policy documents found. Upload your policy documents first."}
    except Exception as e:
        return {"found": False, "message": f"Error searching policies: {str(e)}"}


def _get_academic_calendar(args: dict, user_email: str) -> dict:
    from app.services.rag import get_store
    from app.config import RAGConfig
    year = args.get("year", "")
    query = f"academic calendar {year} term dates holidays".strip()
    store = get_store()
    try:
        chunks = store.search(query, top_k=RAGConfig.TOP_K)
        if chunks:
            texts = "\n\n".join(f"{c['text']}" for c in chunks[:3])
            from app.services.groq_service import generate_answer
            summary = generate_answer(f"Summarize the academic calendar information:\n\n{texts}")
            return {
                "found": True,
                "calendar": summary or texts[:500],
                "sources": [c.get("source", "") for c in chunks[:3]],
            }
        return {"found": False, "message": "No academic calendar found in your documents. Upload one to get started."}
    except Exception as e:
        return {"found": False, "message": f"Error: {str(e)}"}


def _find_exam_schedule(args: dict, user_email: str) -> dict:
    from app.services.rag import get_store
    from app.config import RAGConfig
    exam_type = args.get("exam_type", "")
    class_level = args.get("class", "")
    query = f"exam schedule {exam_type} {class_level} timetable".strip()
    store = get_store()
    try:
        chunks = store.search(query, top_k=RAGConfig.TOP_K)
        if chunks:
            texts = "\n\n".join(f"{c['text']}" for c in chunks[:3])
            from app.services.groq_service import generate_answer
            summary = generate_answer(f"Extract the exam schedule from these documents:\n\n{texts}")
            return {
                "found": True,
                "schedule": summary or texts[:500],
                "sources": [c.get("source", "") for c in chunks[:3]],
            }
        return {"found": False, "message": "No exam schedule found. Upload the exam timetable document first."}
    except Exception as e:
        return {"found": False, "message": f"Error: {str(e)}"}


def _search_student_record(args: dict, user_email: str) -> dict:
    from app.services.rag import get_store
    from app.config import RAGConfig
    query = args["query"]
    student_name = args.get("student_name", "")
    search_query = f"student record {student_name} {query}".strip()
    store = get_store()
    try:
        chunks = store.search(search_query, top_k=RAGConfig.TOP_K)
        if chunks:
            return {
                "found": True,
                "results": [
                    {"source": c.get("source", ""), "excerpt": c.get("text", "")[:300]}
                    for c in chunks[:5]
                ],
                "message": f"Found {min(5, len(chunks))} student record(s) matching your query.",
            }
        return {"found": False, "message": "No student records found. Upload student documents first."}
    except Exception as e:
        return {"found": False, "message": f"Error searching records: {str(e)}"}


def _generate_report_card(args: dict, user_email: str) -> dict:
    student_name = args.get("student_name", "")
    subject = args.get("subject", "")
    performance = args.get("performance", "")
    areas = args.get("areas_for_improvement", "")
    prompt = (
        f"Write a brief report card comment for student {student_name} in {subject}.\n"
        f"Performance: {performance}\n"
        f"Areas for improvement: {areas}\n\n"
        "Keep it constructive, encouraging, and professional (2-3 sentences)."
    )
    try:
        from app.services.groq_service import generate_answer
        comment = generate_answer(prompt)
        return {
            "comment": comment or f"Report card comment for {student_name} - {subject}",
            "student": student_name,
            "subject": subject,
            "message": f"Report card comment generated for {student_name}",
        }
    except Exception as e:
        return {"comment": "", "message": f"Could not generate comment: {str(e)}"}


def _get_hr_overview(args: dict, user_email: str) -> dict:
    from app.modules.hr.routes import overview as _hr_overview

    resp = _hr_overview()
    data = resp.get_json() if hasattr(resp, "get_json") else resp
    return {"overview": data}


def _get_finance_overview(args: dict, user_email: str) -> dict:
    from app.modules.finance.routes import overview as _finance_overview

    resp = _finance_overview()
    data = resp.get_json() if hasattr(resp, "get_json") else resp
    return {"overview": data}


def _get_admissions_overview(args: dict, user_email: str) -> dict:
    from app.modules.admissions.routes import overview as _admissions_overview

    resp = _admissions_overview()
    data = resp.get_json() if hasattr(resp, "get_json") else resp
    return {"overview": data}


def _get_compliance_status(args: dict, user_email: str) -> dict:
    from app.modules.compliance.routes import list_evidence

    resp = list_evidence()
    rows = resp.get_json() if hasattr(resp, "get_json") else resp
    statuses = {"available": 0, "expiring": 0, "missing": 0}
    for r in rows or []:
        s = (r.get("status") or "").lower()
        if s in statuses:
            statuses[s] += 1
        else:
            statuses.setdefault(s, 0)
            statuses[s] += 1
    return {"total_evidence": len(rows or []), "by_status": statuses}


def _get_executive_briefing(args: dict, user_email: str) -> dict:
    from app.modules.executive.routes import overview as _executive_overview

    resp = _executive_overview()
    data = resp.get_json() if hasattr(resp, "get_json") else resp
    return {"overview": data}


def _get_spreadsheet_stats(args: dict, user_email: str) -> dict:
    file_id = (args.get("file_id") or "").strip()
    column = (args.get("column") or "").strip()
    db = _db_session()
    try:
        query = db.query(Document).filter(
            Document.file_path != "",
            Document.file_path.like("%.xlsx"),
        )
        if file_id:
            doc = query.filter(Document.file_id == file_id).first()
        else:
            # ponytail: model may omit file_id; fall back to the user's first
            # spreadsheet so the count still works.
            doc = query.first()
        if not doc or not os.path.exists(doc.file_path):
            return {"error": "Spreadsheet file not found on disk. Re-upload the file."}
        path = doc.file_path
    finally:
        db.close()

    import pandas as pd

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            sheets = pd.read_excel(path, sheet_name=None)
            # ponytail: sheet 0 is often a README/notes sheet; pick the sheet
            # with the most data rows.
            df = max(
                sheets.values(),
                key=lambda s: len(s.dropna(how="all")),
            )
        elif ext == ".csv":
            df = pd.read_csv(path, on_bad_lines="skip")
        else:
            return {"error": "Not a spreadsheet file"}
    except Exception as e:
        return {"error": f"Could not read spreadsheet: {str(e)}"}

    df = df.dropna(how="all")
    if not column:
        return {
            "total_rows": len(df),
            "columns": [str(c) for c in df.columns],
            "message": "Call again with a column name to get exact per-value counts.",
        }

    if column not in df.columns:
        return {
            "error": f"Column '{column}' not found. Available columns: {[str(c) for c in df.columns]}"
        }

    counts = df[column].astype(str).replace({"nan": "(blank)"}).value_counts()
    if df[column].notna().sum() == 0:
        return {
            "column": column,
            "total_rows": len(df),
            "counts": {},
            "message": f"Column '{column}' is empty in the data sheet.",
        }
    top = counts.head(20).to_dict()
    try:
        if pd.api.types.is_datetime64_any_dtype(df[column]) and df[column].notna().any():
            stats = {
                "min": str(df[column].min().date()),
                "max": str(df[column].max().date()),
                "mean": str(df[column].mean().date()),
            }
        else:
            numeric = pd.to_numeric(df[column], errors="coerce")
            if numeric.notna().sum() > 0:
                stats = {
                    "min": float(numeric.min()),
                    "max": float(numeric.max()),
                    "mean": round(float(numeric.mean()), 2),
                }
            else:
                stats = {}
    except Exception:
        stats = {}
    return {
        "column": column,
        "total_rows": len(df),
        "counts": top,
        "stats": stats,
    }


TOOL_EXECUTORS = {
    "apply_leave": _apply_leave,
    "get_leave_balance": _get_leave_balance,
    "list_my_leaves": _list_my_leaves,
    "get_attendance": _get_attendance,
    "mark_attendance": _mark_attendance,
    "get_payslip": _get_payslip,
    "search_hr_policy": _search_hr_policy,
    "get_employee_info": _get_employee_info,
    "get_pending_approvals": _get_pending_approvals,
    "approve_or_reject_request": _approve_or_reject_request,
    "create_invoice": _create_invoice,
    "extract_invoice_data": _extract_invoice_data,
    "list_invoices": _list_invoices,
    "mark_invoice_paid": _mark_invoice_paid,
    "submit_expense": _submit_expense,
    "list_expenses": _list_expenses,
    "get_financial_summary": _get_financial_summary,
    "send_payment_reminder": _send_payment_reminder,
    "schedule_meeting": _schedule_meeting,
    "list_meetings": _list_meetings,
    "register_visitor": _register_visitor,
    "list_assets": _list_assets,
    "add_asset": _add_asset,
    "request_supply": _request_supply,
    "check_inventory": _check_inventory,
    "create_ticket": _create_ticket,
    "list_tickets": _list_tickets,
    "post_announcement": _post_announcement,
    "get_announcements": _get_announcements,
    "onboard_employee": _onboard_employee,
    "generate_hr_report": _generate_hr_report,
    "list_employee_documents": _list_employee_documents,
    "track_payments": _track_payments,
    "reconcile_vendor_statement": _reconcile_vendor_statement,
    "create_accounting_entry": _create_accounting_entry,
    "add_to_audit_storage": _add_to_audit_storage,
    "file_document": _file_document,
    "generate_admin_report": _generate_admin_report,
    "generate_circular_draft": _generate_circular_draft,
    "search_school_policy": _search_school_policy,
    "get_academic_calendar": _get_academic_calendar,
    "find_exam_schedule": _find_exam_schedule,
    "search_student_record": _search_student_record,
    "generate_report_card": _generate_report_card,
    "get_hr_overview": _get_hr_overview,
    "get_finance_overview": _get_finance_overview,
    "get_admissions_overview": _get_admissions_overview,
    "get_compliance_status": _get_compliance_status,
    "get_executive_briefing": _get_executive_briefing,
    "get_spreadsheet_stats": _get_spreadsheet_stats,
}
