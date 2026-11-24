import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Customer, Order, BankTransaction, SettlementReport
from app.models.promises import Promise
from app.extractors.promise_extractor import WhatsAppPromiseExtractor
from app.engines.synthesizer import CaseSynthesizer

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_records(
    orders_file: Optional[UploadFile] = File(None),
    bank_file: Optional[UploadFile] = File(None),
    settlement_file: Optional[UploadFile] = File(None),
    whatsapp_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingests seller files, parses records, runs deterministic reconciliation,
    and updates the case graph.
    """
    summary = {
        "orders_parsed": 0,
        "bank_transactions_parsed": 0,
        "settlements_parsed": 0,
        "promises_extracted": 0,
    }

    # 1. Parse orders.csv if provided
    if orders_file:
        content = (await orders_file.read()).decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            ord_num = row.get("order_number")
            if not ord_num:
                continue
            existing = db.query(Order).filter(Order.order_number == ord_num).first()
            if not existing:
                # Find or create customer
                cust_name = row.get("customer_name", "Walk-in Buyer")
                cust = db.query(Customer).filter(Customer.name == cust_name).first()
                if not cust:
                    cust = Customer(name=cust_name, phone="+919800000000")
                    db.add(cust)
                    db.flush()

                order = Order(
                    customer_id=cust.id,
                    order_number=ord_num,
                    channel=row.get("channel", "Instagram"),
                    order_date=date.fromisoformat(row.get("order_date", "2024-10-01")),
                    gross_amount=Decimal(str(row.get("gross_amount", 0.0))),
                    discount_amount=Decimal(str(row.get("discount_amount", 0.0))),
                    net_amount=Decimal(str(row.get("net_amount", 0.0))),
                    status=row.get("status", "PLACED"),
                    tracking_number=row.get("tracking_number"),
                    notes=row.get("notes"),
                )
                db.add(order)
                summary["orders_parsed"] += 1
        db.commit()

    # 2. Parse bank_statement.csv if provided
    if bank_file:
        content = (await bank_file.read()).decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            utr = row.get("utr_reference")
            if not utr:
                continue
            existing = db.query(BankTransaction).filter(BankTransaction.utr_reference == utr).first()
            if not existing:
                txn = BankTransaction(
                    transaction_date=date.fromisoformat(row.get("transaction_date", "2024-10-01")),
                    transaction_type=row.get("type", "UPI_CR"),
                    amount=Decimal(str(row.get("amount", 0.0))),
                    utr_reference=utr,
                    sender_name=row.get("sender_name"),
                    sender_upi_id=row.get("sender_upi_id"),
                    raw_description=row.get("description", ""),
                )
                db.add(txn)
                summary["bank_transactions_parsed"] += 1
        db.commit()

    # 3. Parse whatsapp_export.txt if provided
    if whatsapp_file:
        content = (await whatsapp_file.read()).decode("utf-8")
        extractor = WhatsAppPromiseExtractor()
        extracted = extractor.extract_from_chat_text(content)
        # Find default customer for uploaded chat
        default_cust = db.query(Customer).first()
        for p in extracted:
            prom = Promise(
                customer_id=default_cust.id if default_cust else "dummy_id",
                channel="WhatsApp",
                timestamp=datetime.utcnow(),
                speaker=p.get("speaker", "SELLER"),
                promise_type=p.get("promise_type", "DELIVERY_DATE"),
                promise_details=p.get("promise_details", ""),
                target_date=date.fromisoformat(p["target_date"]) if p.get("target_date") else None,
                status="UNRECORDED" if p.get("is_adversarial") else "PENDING",
                raw_message_snippet=p.get("raw_snippet", ""),
                confidence_score=Decimal(str(p.get("confidence_score", 0.9))),
            )
            db.add(prom)
            summary["promises_extracted"] += 1
        db.commit()

    # Run case synthesis
    synth = CaseSynthesizer(db)
    created_cases = synth.synthesize_all_cases()
    summary["new_cases_generated"] = len(created_cases)

    return {
        "status": "SUCCESS",
        "summary": summary,
        "message": "Files normalized, deterministic reconciliation executed, and cases updated.",
    }
