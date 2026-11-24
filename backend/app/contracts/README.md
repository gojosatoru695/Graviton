# Jarvis Shared Data Contracts (Pydantic v2)

This package (`app.contracts`) defines the **Single Source of Truth (SSOT)** data models, enums, and error contracts for Project Jarvis.

---

## 1. Architectural Principles

1. **Strict Validation**: All models enforce `strict=True` and `extra="forbid"`. Implicit type coercion (e.g. string to int) is rejected.
2. **Deterministic Arithmetic**: All monetary values strictly use Python's `Decimal` with two decimal places. Floating-point numbers (`float`) are prohibited.
3. **ISO 8601 Temporal Consistency**: All timestamps are timezone-aware UTC `datetime` objects serialized to ISO 8601.
4. **End-to-End Traceability**: Every entity includes a `correlation_id` to trace data flow from raw upload through case synthesis to action receipts.
5. **Full Evidence Provenance**: `EvidenceItem` tracks origin files, line numbers, and immutable snapshot payloads.
6. **Confidence is NOT Proof**: Confidence scores on NLP/LLM extractions (`PromiseRecord`, `EvidenceItem`) are statistical indicators only and are never treated as financial or legal proof.

---

## 2. Team Ownership & Interface Boundaries

To enable concurrent feature development across multiple engineers without git merge conflicts, work is divided across strict ownership boundaries:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        app.contracts (Owner A)                         │
│   Shared, immutable Pydantic v2 models, Enums, and Error Codes         │
└───────────────────▲────────────────────────────────▲───────────────────┘
                    │                                │
         Consumes contracts               Consumes contracts
                    │                                │
┌───────────────────┴───────────────┐ ┌──────────────┴───────────────────┐
│              OWNER B              │ │              OWNER C              │
│   Deterministic Engines & Math    │ │   Extraction, Comms & Execution   │
├───────────────────────────────────┤ ├───────────────────────────────────┤
│ • app/engines/reconciler.py       │ │ • app/extractors/promise_ext.py   │
│ • app/engines/variance.py         │ │ • app/extractors/injection_gd.py  │
│ • app/engines/synthesizer.py      │ │ • app/services/razorpay_svc.py    │
│ • tests/test_engines.py           │ │ • app/services/gmail_svc.py       │
│                                   │ │ • app/services/receipt_svc.py     │
│ In: BankTransaction, OrderRecord  │ │ In: InboundEnvelope, CommsContext │
│ Out: PaymentRecord, Finding, Case │ │ Out: PromiseRecord, ActionProposal│
└───────────────────────────────────┘ └───────────────────────────────────┘
```

### Owner Roles
- **Owner A (Platform / Architect)**: Owns `app/contracts/`. This package is treated as an immutable API.
- **Owner B (Financial Engine Engineer)**:
  - Owns deterministic reconciliation, payment matching, settlement deduction waterfalls, and arithmetic findings.
  - Consumes: `OrderRecord`, `BankTransaction`, `SettlementLine`.
  - Produces: `PaymentRecord`, `Finding`, `CommercialCase`, `PolicyDecision`.
  - Works strictly within `app/engines/` and `tests/test_engines.py`.
- **Owner C (Comms, Promise Extractor & Gateway Engineer)**:
  - Owns WhatsApp/Instagram message normalization, Gemini promise extraction, prompt-injection defense, and sandbox gateways (Razorpay, Gmail).
  - Consumes: `InboundEnvelope`, `NormalizedCommsContext`, `ActionProposal`, `ApprovalDecision`.
  - Produces: `PromiseRecord`, `ActionProposal`, `DeliveryResult`, `PaymentLinkResult`, `ActionReceipt`.
  - Works strictly within `app/extractors/`, `app/services/`, and `tests/test_services.py`.

---

## 3. Merge Conflict Prevention Strategy

Owners B and C can build, test, and ship simultaneously without code conflicts by adhering to these four rules:

### Rule 1: Zero Direct Edits to `app/contracts/`
Neither Owner B nor Owner C modifies files inside `app/contracts/`. If a field or enum value must be added, an RFC issue is raised to Owner A.

### Rule 2: Strict Directory Isolation
- Owner B commits only to `app/engines/` and `tests/test_engines*`.
- Owner C commits only to `app/extractors/`, `app/services/`, and `tests/test_extractors*`.
- Git branches touch disjoint sets of files, guaranteeing conflict-free rebases and merges.

### Rule 3: Decoupled Mock-Driven Testing
- Owner B tests engines using synthetic `BankTransaction` and `OrderRecord` fixtures without depending on Owner C's extraction scripts.
- Owner C tests promise extraction and Razorpay/Gmail sandbox gateways without depending on Owner B's financial reconciliation code.

### Rule 4: Type-Safe Named Imports
Both owners import directly from the top-level contracts module:
```python
from app.contracts import (
    BankTransaction,
    OrderRecord,
    PaymentStatus,
    CommercialCase,
    ErrorCode,
)
```

---

## 4. Consumption Guide

### How Owner B Consumes Contracts (Deterministic Engine)
```python
from decimal import Decimal
from typing import List
from app.contracts import (
    BankTransaction,
    OrderRecord,
    PaymentRecord,
    PaymentStatus,
    Finding,
    Severity,
)

def reconcile_payment(order: OrderRecord, credit: BankTransaction) -> PaymentRecord:
    # Deterministic Decimal matching (Zero LLM, Zero Float)
    if credit.amount == order.net_amount:
        status = PaymentStatus.PAID
        shortfall = Decimal("0.00")
    elif credit.amount < order.net_amount:
        status = PaymentStatus.PARTIALLY_PAID
        shortfall = order.net_amount - credit.amount
    else:
        status = PaymentStatus.DUPLICATE_CANDIDATE
        shortfall = Decimal("0.00")

    return PaymentRecord(
        correlation_id=order.correlation_id,
        order_id=order.order_id,
        bank_transaction_id=credit.transaction_id,
        expected_amount=order.net_amount,
        paid_amount=credit.amount,
        shortfall_amount=shortfall,
        status=status,
    )
```

### How Owner C Consumes Contracts (Extraction & Gateway)
```python
from decimal import Decimal
from app.contracts import (
    NormalizedCommsContext,
    PromiseRecord,
    PromiseType,
    PromiseStatus,
    ActionProposal,
    ActionType,
)

def extract_promise_contract(context: NormalizedCommsContext) -> PromiseRecord:
    return PromiseRecord(
        correlation_id=context.correlation_id,
        customer_id="cust_101",
        speaker="SELLER",
        promise_type=PromiseType.FREE_GIFT,
        promise_details="Complimentary silk scrunchie gift",
        raw_message_snippet=context.raw_text,
        confidence_score=Decimal("0.95"),  # Informational only, never proof!
        status=PromiseStatus.PENDING,
    )
```

---

## 5. Contract Validation & Error Handling

When raising exceptions, use `JarvisContractException` with the standardized `ErrorCode`:

```python
from app.contracts import ErrorCode, JarvisContractException, ErrorDetail

if not row.get("order_number"):
    raise JarvisContractException(
        code=ErrorCode.MISSING_REQUIRED_COLUMN,
        message="CSV row missing required column 'order_number'.",
        correlation_id=envelope.correlation_id,
        details=[ErrorDetail(field="order_number", message="Column empty or absent.")],
    )
```
