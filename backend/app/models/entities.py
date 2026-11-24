import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Numeric,
    Date,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    instagram_handle = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    promises = relationship("Promise", back_populates="customer", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    order_number = Column(String(50), unique=True, nullable=False)
    channel = Column(String(30), nullable=False)  # Instagram, WhatsApp, Website, Meesho
    order_date = Column(Date, nullable=False)
    gross_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    net_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(30), nullable=False)  # PLACED, SHIPPED, DELIVERED, CANCELLED
    expected_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)
    tracking_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="orders")
    invoices = relationship("Invoice", back_populates="order", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", back_populates="matched_order")
    promises = relationship("Promise", back_populates="order")
    cases = relationship("Case", back_populates="order")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)
    invoice_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    pdf_path = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="invoices")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_date = Column(Date, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # UPI_CR, NEFT, IMPS
    amount = Column(Numeric(10, 2), nullable=False)
    utr_reference = Column(String(50), unique=True, nullable=False)
    sender_name = Column(String(100), nullable=True)
    sender_upi_id = Column(String(100), nullable=True)
    raw_description = Column(Text, nullable=False)
    matched_order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    reconciliation_status = Column(String(30), nullable=False, default="UNMATCHED")  # MATCHED, PARTIAL, UNMATCHED, DUPLICATE_CANDIDATE

    matched_order = relationship("Order", back_populates="bank_transactions")


class SettlementReport(Base):
    __tablename__ = "settlement_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marketplace = Column(String(50), nullable=False)  # Meesho, Amazon
    settlement_id = Column(String(50), unique=True, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    gross_order_value = Column(Numeric(10, 2), nullable=False)
    commission_fee = Column(Numeric(10, 2), nullable=False)
    logistics_fee = Column(Numeric(10, 2), nullable=False)
    return_penalties = Column(Numeric(10, 2), nullable=False)
    taxes_tcs_tds = Column(Numeric(10, 2), nullable=False)
    net_settlement_payable = Column(Numeric(10, 2), nullable=False)
    actual_bank_credit = Column(Numeric(10, 2), nullable=False)
    unexplained_residual = Column(Numeric(10, 2), nullable=False)
    bank_utr = Column(String(50), nullable=True)

    line_items = relationship("SettlementLineItem", back_populates="settlement_report", cascade="all, delete-orphan")


class SettlementLineItem(Base):
    __tablename__ = "settlement_line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    settlement_id = Column(String(36), ForeignKey("settlement_reports.id"), nullable=False)
    order_reference = Column(String(50), nullable=False)
    gross_amount = Column(Numeric(10, 2), nullable=False)
    deductions_breakdown = Column(JSON, nullable=False)  # {'commission': ..., 'shipping': ...}
    net_amount = Column(Numeric(10, 2), nullable=False)
    matched_order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)

    settlement_report = relationship("SettlementReport", back_populates="line_items")
