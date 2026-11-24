import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    case_type = Column(String(50), nullable=False)  # PAYMENT_SHORTFALL, DUPLICATE_PAYMENT, MARKETPLACE_VARIANCE, BROKEN_PROMISE, UNRECORDED_GIFT
    severity = Column(String(20), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(30), nullable=False, default="OPEN")  # OPEN, PENDING_APPROVAL, ACTION_EXECUTED, RESOLVED, DISMISSED
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    discrepancy_amount = Column(Numeric(10, 2), default=0.00)
    headline = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="cases")
    order = relationship("Order", back_populates="cases")
    evidence_items = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")
    pending_actions = relationship("PendingAction", back_populates="case", cascade="all, delete-orphan")
    receipts = relationship("ActionReceipt", back_populates="case", cascade="all, delete-orphan")


class CaseEvidence(Base):
    __tablename__ = "case_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    evidence_type = Column(String(50), nullable=False)  # ORDER, BANK_TXN, PROMISE, INVOICE, SETTLEMENT_LINE, CHAT_SNIPPET
    source_table = Column(String(50), nullable=False)
    source_id = Column(String(36), nullable=False)
    content_payload = Column(JSON, nullable=False)

    case = relationship("Case", back_populates="evidence_items")


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # RAZORPAY_PAYMENT_LINK, GMAIL_DRAFT, SETTLEMENT_DISPUTE_PACK
    target_recipient = Column(String(100), nullable=False)
    action_summary = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED, EXECUTED
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="pending_actions")
    receipt = relationship("ActionReceipt", uselist=False, back_populates="pending_action")


class ActionReceipt(Base):
    __tablename__ = "action_receipts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pending_action_id = Column(String(36), ForeignKey("pending_actions.id"), unique=True, nullable=False)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    decision = Column(String(20), nullable=False)  # APPROVED, REJECTED
    actor = Column(String(50), nullable=False)  # e.g., "Seller (Manual HITL)"
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    payload_snapshot = Column(JSON, nullable=False)
    execution_result = Column(JSON, nullable=False)
    receipt_hash = Column(String(64), nullable=False)  # SHA-256
    tamper_chain_previous_hash = Column(String(64), nullable=True)

    pending_action = relationship("PendingAction", back_populates="receipt")
    case = relationship("Case", back_populates="receipts")
