"""
Jarvis Deterministic Normalizer Service.
Handles CSV ingestion, flexible column mapping, strict validation, and normalization
into shared Pydantic v2 data contracts.

Rules:
- Strictly Decimal for all currency fields. Never float.
- Transparent and helpful error reporting when required columns are absent.
- Standardizes Indian date formats (DD/MM/YYYY, YYYY-MM-DD, etc.) to Python date / ISO 8601.
- Standardizes Indian monetary amounts (removes commas, handles currency signs).
"""

import csv
import io
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union

from app.contracts.enums import PaymentStatus
from app.contracts.errors import ErrorCode, ErrorDetail, JarvisContractException
from app.contracts.models import (
    BankTransaction,
    DeliveryRecord,
    InvoiceRecord,
    OrderRecord,
    SettlementLine,
)


def generate_uuid() -> str:
    return str(uuid.uuid4())


# -----------------------------------------------------------------------------
# Column Mapping Dictionaries with Synonyms
# -----------------------------------------------------------------------------
ORDER_COLUMN_ALIASES: Dict[str, List[str]] = {
    "order_number": ["order_number", "order_id", "order_no", "order_ref", "invoice_no"],
    "channel": ["channel", "source", "sales_channel", "platform"],
    "customer_name": ["customer_name", "customer", "buyer_name", "client_name", "name"],
    "order_date": ["order_date", "date", "created_at", "booking_date"],
    "gross_amount": ["gross_amount", "gross", "order_total", "item_total", "subtotal_amount"],
    "discount_amount": ["discount_amount", "discount", "disc", "promo_discount"],
    "net_amount": ["net_amount", "net", "total_amount", "amount_payable", "final_amount", "order_amount"],
    "status": ["status", "order_status", "fulfillment_status", "delivery_status"],
}

INVOICE_COLUMN_ALIASES: Dict[str, List[str]] = {
    "invoice_number": ["invoice_number", "invoice_id", "invoice_no", "inv_no", "bill_no"],
    "order_number": ["order_number", "order_id", "order_ref", "linked_order"],
    "customer_name": ["customer_name", "customer", "billing_name", "client_name"],
    "invoice_date": ["invoice_date", "date", "issue_date"],
    "subtotal": ["subtotal", "taxable_value", "taxable_amount", "base_amount"],
    "tax_amount": ["tax_amount", "gst_amount", "tax", "cgst_sgst"],
    "total_amount": ["total_amount", "invoice_total", "grand_total", "total", "amount"],
}

BANK_COLUMN_ALIASES: Dict[str, List[str]] = {
    "transaction_date": ["transaction_date", "txn_date", "date", "value_date", "posting_date"],
    "type": ["type", "txn_type", "transaction_type", "cr_dr", "dr_cr"],
    "amount": ["amount", "txn_amount", "credit", "credit_amount", "deposit"],
    "utr_reference": ["utr_reference", "utr", "rrn", "reference_no", "ref_no", "txn_id", "reference"],
    "narration": ["narration", "description", "particulars", "remarks", "raw_narration"],
}

SETTLEMENT_COLUMN_ALIASES: Dict[str, List[str]] = {
    "settlement_id": ["settlement_id", "batch_id", "statement_id", "settlement_reference"],
    "marketplace": ["marketplace", "platform", "source"],
    "gross_order_value": ["gross_order_value", "gross_sales", "gross_amount", "total_sales"],
    "commission_fee": ["commission_fee", "marketplace_commission", "commission", "platform_fee"],
    "shipping_fee": ["shipping_fee", "logistics_fee", "courier_fee", "shipping_charge"],
    "return_rto_fee": ["return_rto_fee", "return_fee", "rto_fee", "reverse_logistics"],
    "tax_deduction_tcs_tds": ["tax_deduction_tcs_tds", "tax_deduction", "tcs_tds_tax", "tds_tcs", "taxes"],
    "expected_net_payable": ["expected_net_payable", "expected_net", "expected_payout", "net_payable"],
    "actual_bank_credit": ["actual_bank_credit", "actual_credit", "disbursed_amount", "bank_deposit"],
}

DELIVERY_COLUMN_ALIASES: Dict[str, List[str]] = {
    "order_number": ["order_number", "order_id", "order_no"],
    "carrier": ["carrier", "courier", "logistics_partner", "courier_name"],
    "tracking_awb": ["tracking_awb", "tracking_number", "awb", "docket_no", "tracking_id"],
    "dispatch_date": ["dispatch_date", "shipped_date", "dispatch_time"],
    "delivery_status": ["delivery_status", "status", "shipment_status"],
}


# -----------------------------------------------------------------------------
# Parser Utility Functions
# -----------------------------------------------------------------------------
def parse_indian_money(raw_value: Any) -> Decimal:
    """
    Deterministically parses an Indian currency string or numeric into a 2-decimal Decimal.
    Handles currency symbols (₹, Rs, Rs.), commas, whitespace, and negative values.
    """
    if raw_value is None:
        return Decimal("0.00")
    if isinstance(raw_value, Decimal):
        return raw_value.quantize(Decimal("0.01"))
    if isinstance(raw_value, (int, float)):
        return Decimal(str(raw_value)).quantize(Decimal("0.01"))

    cleaned = str(raw_value).strip()
    if not cleaned:
        return Decimal("0.00")

    # Remove currency symbols and formatting characters
    cleaned = re.sub(r"[₹\$\€\£]", "", cleaned)
    cleaned = re.sub(r"(?i)(inr|rs\.?)\s*", "", cleaned)
    cleaned = cleaned.replace(",", "").strip()

    # Handle parenthesized negative notation like (150.00)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"

    try:
        val = Decimal(cleaned)
        return val.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as err:
        raise ValueError(f"Invalid monetary format '{raw_value}': unable to parse as Decimal.") from err


def parse_date_flexible(raw_value: Any) -> date:
    """
    Parses varied human or machine date formats into a standard Python date:
    - DD/MM/YYYY, DD-MM-YYYY
    - YYYY-MM-DD, YYYY/MM/DD
    - DD/MM/YY
    - ISO 8601 timestamps
    """
    if raw_value is None:
        raise ValueError("Date value is null/empty.")
    if isinstance(raw_value, date) and not isinstance(raw_value, datetime):
        return raw_value
    if isinstance(raw_value, datetime):
        return raw_value.date()

    cleaned = str(raw_value).strip()
    if not cleaned:
        raise ValueError("Date string is empty.")

    # ISO formats YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cleaned)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        return date(y, m, d)

    # Indian formats DD/MM/YYYY or DD-MM-YYYY
    in_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", cleaned)
    if in_match:
        d, m, y = int(in_match.group(1)), int(in_match.group(2)), int(in_match.group(3))
        return date(y, m, d)

    # Short year DD/MM/YY
    in_short = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2})", cleaned)
    if in_short:
        d, m, y_short = int(in_short.group(1)), int(in_short.group(2)), int(in_short.group(3))
        y = 2000 + y_short if y_short < 70 else 1900 + y_short
        return date(y, m, d)

    # Fallback to date.fromisoformat
    try:
        return date.fromisoformat(cleaned[:10])
    except ValueError as err:
        raise ValueError(f"Unrecognized date format '{raw_value}'. Expected DD/MM/YYYY or YYYY-MM-DD.") from err


def map_columns(
    headers: List[str],
    aliases_spec: Dict[str, List[str]],
    required_keys: List[str],
    source_filename: str,
    correlation_id: str,
) -> Dict[str, str]:
    """
    Maps incoming CSV headers to canonical contract keys using synonym lists.
    Raises JarvisContractException with ErrorCode.MISSING_REQUIRED_COLUMN if any required key is unmapped.
    """
    clean_headers = {h.strip().lower().replace(" ", "_"): h for h in headers if h}
    mapping: Dict[str, str] = {}

    for canonical_key, synonyms in aliases_spec.items():
        found = False
        for syn in synonyms:
            clean_syn = syn.lower().replace(" ", "_")
            if clean_syn in clean_headers:
                mapping[canonical_key] = clean_headers[clean_syn]
                found = True
                break
        if not found and canonical_key in required_keys:
            # Missing a mandatory required column
            details = [
                ErrorDetail(
                    field=canonical_key,
                    message=f"Missing required column for '{canonical_key}'. Expected one of: {synonyms}",
                    rejected_value=headers,
                )
            ]
            raise JarvisContractException(
                code=ErrorCode.MISSING_REQUIRED_COLUMN,
                message=f"File '{source_filename}' is missing required column '{canonical_key}'.",
                correlation_id=correlation_id,
                details=details,
                context={"headers": headers, "expected_column": canonical_key, "aliases": synonyms},
            )

    return mapping


def read_csv_rows(csv_content_or_path: str, correlation_id: str, source_filename: str) -> List[Dict[str, str]]:
    """
    Reads CSV rows from a raw string or file path, validating CSV syntax.
    """
    if not csv_content_or_path or not csv_content_or_path.strip():
        raise JarvisContractException(
            code=ErrorCode.FILE_PARSE_ERROR,
            message=f"File '{source_filename}' is empty.",
            correlation_id=correlation_id,
        )

    # Determine if it's a file path or raw string
    lines = None
    if "\n" not in csv_content_or_path and (csv_content_or_path.endswith(".csv") or csv_content_or_path.endswith(".txt")):
        try:
            with open(csv_content_or_path, mode="r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(csv_content_or_path, mode="r", encoding="latin-1") as f:
                content = f.read()
        except Exception as e:
            raise JarvisContractException(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"Failed to read file '{csv_content_or_path}': {str(e)}",
                correlation_id=correlation_id,
            ) from e
    else:
        content = csv_content_or_path

    try:
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise JarvisContractException(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"File '{source_filename}' has no header columns.",
                correlation_id=correlation_id,
            )
        rows = list(reader)
        return rows
    except csv.Error as e:
        raise JarvisContractException(
            code=ErrorCode.FILE_PARSE_ERROR,
            message=f"Malformed CSV in '{source_filename}': {str(e)}",
            correlation_id=correlation_id,
        ) from e


# -----------------------------------------------------------------------------
# Entity Normalizers
# -----------------------------------------------------------------------------
def normalize_orders(
    csv_data: str,
    correlation_id: str,
    source_filename: str = "orders.csv"
) -> List[OrderRecord]:
    """
    Parses and normalizes orders CSV into strict OrderRecord contract instances.
    """
    rows = read_csv_rows(csv_data, correlation_id, source_filename)
    if not rows:
        return []

    headers = list(rows[0].keys())
    required = ["order_number", "customer_name", "order_date", "gross_amount", "net_amount"]
    col_map = map_columns(headers, ORDER_COLUMN_ALIASES, required, source_filename, correlation_id)

    order_records: List[OrderRecord] = []
    for idx, row in enumerate(rows, start=2):
        ord_num = row.get(col_map["order_number"], "").strip()
        cust_name = row.get(col_map["customer_name"], "").strip()
        ord_date_raw = row.get(col_map["order_date"], "").strip()
        gross_raw = row.get(col_map["gross_amount"], "0")
        net_raw = row.get(col_map["net_amount"], "0")

        disc_col = col_map.get("discount_amount")
        disc_raw = row.get(disc_col, "0") if disc_col else "0"

        channel_col = col_map.get("channel")
        channel = row.get(channel_col, "Direct").strip() if channel_col else "Direct"

        status_col = col_map.get("status")
        status = row.get(status_col, "PLACED").strip().upper() if status_col else "PLACED"

        cust_id = row.get("customer_id", "").strip() or f"CUST-{re.sub(r'[^A-Za-z0-9]', '', cust_name).upper()[:8]}"

        try:
            ord_date = parse_date_flexible(ord_date_raw)
            gross = parse_indian_money(gross_raw)
            disc = parse_indian_money(disc_raw)
            net = parse_indian_money(net_raw)
        except Exception as e:
            raise JarvisContractException(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"Row {idx} in '{source_filename}' has invalid numerical or date format: {str(e)}",
                correlation_id=correlation_id,
                details=[ErrorDetail(field="row", message=str(e), rejected_value=row)],
            ) from e

        # Optional fields
        exp_del = None
        if "expected_delivery_date" in row and row["expected_delivery_date"].strip():
            try:
                exp_del = parse_date_flexible(row["expected_delivery_date"].strip())
            except Exception:
                exp_del = None

        act_del = None
        if "actual_delivery_date" in row and row["actual_delivery_date"].strip():
            try:
                act_del = parse_date_flexible(row["actual_delivery_date"].strip())
            except Exception:
                act_del = None

        tracking = row.get("tracking_number", "").strip() or None
        notes = row.get("notes", "").strip() or None

        rec = OrderRecord(
            order_id=f"ord_{ord_num.lower()}",
            correlation_id=correlation_id,
            order_number=ord_num,
            channel=channel,
            customer_id=cust_id,
            order_date=ord_date,
            gross_amount=gross,
            discount_amount=disc,
            net_amount=net,
            status=status,
            expected_delivery_date=exp_del,
            actual_delivery_date=act_del,
            tracking_number=tracking,
            notes=notes,
        )
        order_records.append(rec)

    return order_records


def normalize_invoices(
    csv_data: str,
    correlation_id: str,
    source_filename: str = "invoices.csv"
) -> List[InvoiceRecord]:
    """
    Parses and normalizes invoices CSV into InvoiceRecord instances.
    """
    rows = read_csv_rows(csv_data, correlation_id, source_filename)
    if not rows:
        return []

    headers = list(rows[0].keys())
    required = ["invoice_number", "order_number", "invoice_date", "subtotal", "total_amount"]
    col_map = map_columns(headers, INVOICE_COLUMN_ALIASES, required, source_filename, correlation_id)

    invoices: List[InvoiceRecord] = []
    for idx, row in enumerate(rows, start=2):
        inv_num = row.get(col_map["invoice_number"], "").strip()
        ord_num = row.get(col_map["order_number"], "").strip()
        inv_date_raw = row.get(col_map["invoice_date"], "").strip()
        subtotal_raw = row.get(col_map["subtotal"], "0")
        total_raw = row.get(col_map["total_amount"], "0")

        tax_col = col_map.get("tax_amount")
        tax_raw = row.get(tax_col, "0") if tax_col else "0"

        try:
            inv_date = parse_date_flexible(inv_date_raw)
            subtotal = parse_indian_money(subtotal_raw)
            total = parse_indian_money(total_raw)
            tax = parse_indian_money(tax_raw) if tax_col else (total - subtotal)
        except Exception as e:
            raise JarvisContractException(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"Row {idx} in '{source_filename}' has invalid numbers or dates: {str(e)}",
                correlation_id=correlation_id,
            ) from e

        rec = InvoiceRecord(
            invoice_id=f"inv_{inv_num.lower()}",
            correlation_id=correlation_id,
            order_id=f"ord_{ord_num.lower()}",
            invoice_number=inv_num,
            invoice_date=inv_date,
            subtotal=subtotal,
            tax_amount=tax,
            total_amount=total,
            document_uri=row.get("pdf_filename") or f"{inv_num}.pdf",
        )
        invoices.append(rec)

    return invoices


def normalize_bank_statement(
    csv_data: str,
    correlation_id: str,
    source_filename: str = "bank_statement.csv"
) -> List[BankTransaction]:
    """
    Parses and normalizes bank statement transactions.
    Extracts UPI RRN, narration keywords, and cleans positive/negative amounts.
    """
    rows = read_csv_rows(csv_data, correlation_id, source_filename)
    if not rows:
        return []

    headers = list(rows[0].keys())
    required = ["transaction_date", "type", "amount", "narration"]
    col_map = map_columns(headers, BANK_COLUMN_ALIASES, required, source_filename, correlation_id)

    transactions: List[BankTransaction] = []
    for idx, row in enumerate(rows, start=2):
        d_raw = row.get(col_map["transaction_date"], "").strip()
        t_type = row.get(col_map["type"], "UPI_CR").strip().upper()
        amt_raw = row.get(col_map["amount"], "0")
        narration = row.get(col_map["narration"], "").strip()

        utr_col = col_map.get("utr_reference")
        utr = row.get(utr_col, "").strip() if utr_col else ""

        sender_name = row.get("sender_name", "").strip() or None
        sender_upi_id = row.get("sender_upi_id", "").strip() or None

        try:
            t_date = parse_date_flexible(d_raw)
            raw_amt = parse_indian_money(amt_raw)
            # Contract enforces ge=Decimal('0.00'). For debits/refunds, amount is unsigned,
            # and type indicates UPI_DR or DEBIT/REFUND.
            abs_amount = abs(raw_amt)
            if raw_amt < Decimal("0.00") and "DR" not in t_type:
                t_type = "UPI_DR"
        except Exception as e:
            raise JarvisContractException(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"Row {idx} in '{source_filename}' has invalid date or amount: {str(e)}",
                correlation_id=correlation_id,
            ) from e

        # Fallback UTR extraction from narration if not provided
        if not utr:
            rrn_match = re.search(r"\b(\d{10,12})\b", narration)
            utr = rrn_match.group(1) if rrn_match else f"REF-{idx:04d}"

        # If sender_name not provided, extract from UPI narration if possible
        if not sender_name:
            upi_name_match = re.search(r"/(?:CR|DR)/\d+/([^/]+)", narration)
            if upi_name_match:
                sender_name = upi_name_match.group(1)

        txn_id = f"txn_{utr.lower()}_{idx}"

        rec = BankTransaction(
            transaction_id=txn_id,
            correlation_id=correlation_id,
            transaction_date=t_date,
            transaction_type=t_type,
            amount=abs_amount,
            utr_reference=utr,
            sender_name=sender_name,
            sender_upi_id=sender_upi_id,
            raw_narration=narration,
            matched_order_id=None,
            payment_status=PaymentStatus.UNMATCHED_CREDIT,
        )
        transactions.append(rec)

    return transactions


def normalize_settlement_report(
    csv_data: str,
    correlation_id: str,
    source_filename: str = "settlement_report.csv"
) -> List[Dict[str, Any]]:
    """
    Parses and normalizes settlement statement rows into a list of structured dictionaries
    with Decimal math ready for settlement variance calculation.
    """
    rows = read_csv_rows(csv_data, correlation_id, source_filename)
    if not rows:
        return []

    headers = list(rows[0].keys())
    required = [
        "settlement_id",
        "gross_order_value",
        "commission_fee",
        "shipping_fee",
        "expected_net_payable",
        "actual_bank_credit",
    ]
    col_map = map_columns(headers, SETTLEMENT_COLUMN_ALIASES, required, source_filename, correlation_id)

    normalized_settlements: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows, start=2):
        s_id = row.get(col_map["settlement_id"], f"STMT-{idx}").strip()
        mkt_col = col_map.get("marketplace")
        mkt = row.get(mkt_col, "Meesho").strip() if mkt_col else "Meesho"

        try:
            gross = parse_indian_money(row.get(col_map["gross_order_value"], "0"))
            comm = parse_indian_money(row.get(col_map["commission_fee"], "0"))
            shipping = parse_indian_money(row.get(col_map["shipping_fee"], "0"))

            rto_col = col_map.get("return_rto_fee")
            rto = parse_indian_money(row.get(rto_col, "0")) if rto_col else Decimal("0.00")

            tax_col = col_map.get("tax_deduction_tcs_tds")
            tax = parse_indian_money(row.get(tax_col, "0")) if tax_col else Decimal("0.00")

            other_adj_val = Decimal("0.00")
            for k in ["other_known_adjustment", "known_adjustments", "adjustments"]:
                if k in row:
                    other_adj_val = parse_indian_money(row[k])
                    break

            expected_net = parse_indian_money(row.get(col_map["expected_net_payable"], "0"))
            actual_credit = parse_indian_money(row.get(col_map["actual_bank_credit"], "0"))
        except Exception as e:
            raise JarvisContractException(
                code=ErrorCode.FILE_PARSE_ERROR,
                message=f"Row {idx} in '{source_filename}' has invalid monetary fields: {str(e)}",
                correlation_id=correlation_id,
            ) from e

        # Extract itemized unexplained deductions if present
        unexplained_items: List[str] = []
        for k in ["unexplained_deduction_1", "unexplained_deduction_2", "unexplained_reasons"]:
            if k in row and row[k].strip():
                unexplained_items.append(row[k].strip())

        utr = row.get("bank_utr_reference") or row.get("utr_reference") or ""

        normalized_settlements.append({
            "settlement_id": s_id,
            "marketplace": mkt,
            "gross_order_value": gross,
            "commission_fee": comm,
            "shipping_fee": shipping,
            "return_rto_fee": rto,
            "tax_deduction_tcs_tds": tax,
            "other_known_adjustment": other_adj_val,
            "expected_net_payable": expected_net,
            "actual_bank_credit": actual_credit,
            "bank_utr_reference": utr,
            "unexplained_deductions": unexplained_items,
            "raw_row": row,
        })

    return normalized_settlements
