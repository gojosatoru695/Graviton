import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Numeric,
    Date,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Promise(Base):
    __tablename__ = "promises"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    channel = Column(String(30), default="WhatsApp")
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    speaker = Column(String(20), nullable=False)  # SELLER, CUSTOMER
    promise_type = Column(String(50), nullable=False)  # DELIVERY_DATE, FREE_GIFT, DISCOUNT, CUSTOMIZATION, PAYMENT_COMMITMENT
    promise_details = Column(Text, nullable=False)
    target_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="PENDING")  # PENDING, KEPT, BROKEN, UNRECORDED
    raw_message_snippet = Column(Text, nullable=False)
    confidence_score = Column(Numeric(3, 2), nullable=False, default=1.00)

    customer = relationship("Customer", back_populates="promises")
    order = relationship("Order", back_populates="promises")
