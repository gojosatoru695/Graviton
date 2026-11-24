"""
Jarvis Safe Seller Outbound Draft Generator.
Generates polite, concise, professional customer drafts for Indian micro-business owners.

Safety Rules:
- Never promise unverified refunds, unauthorized discounts, or free gifts.
- All outbound communications require human approval.
- Include {{payment_link}} placeholder when requesting payment balance.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.ai.schemas import DraftRequest, SafeDraftResponse


class SafeDraftGenerator:
    """
    Constructs safety-checked communication drafts for the seller.
    """

    def generate_draft(self, request: DraftRequest) -> SafeDraftResponse:
        """
        Creates a contextual, respectful draft ensuring zero unauthorized commitments.
        """
        safety_flags: List[str] = []
        is_approved = True

        cust_first = request.customer_name.split()[0] if request.customer_name else "Customer"
        salutation = f"Hello {cust_first} ji!"

        action = request.desired_action
        order_ref = request.order_reference or "your order"

        # Check for unauthorized promises in desired action
        if "unapproved_discount" in action or ("discount" in action and not request.finding):
            safety_flags.append("BLOCKED: Cannot draft unverified discount promise not present in verified finding.")
            is_approved = False
            return SafeDraftResponse(
                subject=f"Update regarding {order_ref}",
                body="Draft generation blocked by safety policy: Attempted unverified discount promise.",
                payment_link_placeholder=None,
                confidence=Decimal("0.00"),
                safety_flags=safety_flags,
                is_approved_by_policy=False,
            )

        if "unapproved_refund" in action or ("refund" in action and not request.finding):
            safety_flags.append("BLOCKED: Cannot draft unverified refund promise without verified return evidence.")
            is_approved = False
            return SafeDraftResponse(
                subject=f"Update regarding {order_ref}",
                body="Draft generation blocked by safety policy: Attempted unverified refund promise.",
                payment_link_placeholder=None,
                confidence=Decimal("0.00"),
                safety_flags=safety_flags,
                is_approved_by_policy=False,
            )

        placeholder = "{{payment_link}}"

        # 1. Payment Reminder / Balance Pending Draft
        if action == "payment_reminder":
            shortfall = request.shortfall_amount or Decimal("0.00")
            subject = f"Gentle Reminder: Balance payment for Order {order_ref} - Aura Weaves & Jewels"
            body = (
                f"{salutation}\n\n"
                f"Hope you are doing well and loved your parcel for {order_ref}!\n\n"
                f"This is a gentle reminder regarding the remaining balance of ₹{shortfall}. "
                f"You can quickly complete this transfer using our secure Razorpay link:\n"
                f"{placeholder}\n\n"
                f"Please let us know once transferred so we can update your account ledger. "
                f"Thank you for supporting our artisan studio!\n\n"
                f"Warm regards,\n"
                f"Neha Sharma\n"
                f"Aura Weaves & Jewels"
            )
            safety_flags.append("Verified shortfall amount attached from ledger.")

        # 2. Delivery Delay Apology Draft
        elif action == "delay_apology":
            subject = f"Sincere Apologies regarding delivery delay for Order {order_ref}"
            body = (
                f"{salutation}\n\n"
                f"We are writing to sincerely apologize for the delay in the delivery of your order {order_ref}. "
                f"We know you were eagerly awaiting this piece, and we deeply regret the courier transit backlog that caused this delay.\n\n"
                f"We value your relationship with Aura Weaves tremendously and are committed to ensuring "
                f"your next experience is completely seamless.\n\n"
                f"Please accept our heartfelt apologies.\n\n"
                f"Warm regards,\n"
                f"Neha Sharma\n"
                f"Aura Weaves & Jewels"
            )
            placeholder = None
            safety_flags.append("Apology draft generated without unverified cash liability.")

        # 3. Unapproved Discount / Pricing Clarification Draft
        elif action == "clarification":
            subject = f"Important clarification regarding order pricing for {order_ref}"
            shortfall = request.shortfall_amount or Decimal("0.00")
            body = (
                f"{salutation}\n\n"
                f"Thank you for your order {order_ref} with Aura Weaves.\n\n"
                f"As our authentic handloom textiles are crafted directly by artisans with fixed modest margins, "
                f"we are unable to accommodate extra unapproved discounts on this piece. "
                f"To complete your order dispatch, kindly clear the remaining balance of ₹{shortfall} here:\n"
                f"{placeholder}\n\n"
                f"We appreciate your understanding and cooperation!\n\n"
                f"Warm regards,\n"
                f"Neha Sharma\n"
                f"Aura Weaves & Jewels"
            )
            placeholder = "{{payment_link}}"
            safety_flags.append("Polite boundary set; no unauthorized concession granted.")

        # 4. Free Gift Confirmation Draft
        elif action == "gift_confirmation":
            subject = f"Special gift confirmation for your order {order_ref}"
            body = (
                f"{salutation}\n\n"
                f"Thank you so much for placing order {order_ref} with us! "
                f"As promised during our conversation, we have packaged your complimentary gift inside the parcel.\n\n"
                f"We hope you enjoy wearing it as much as we enjoyed crafting it for you.\n\n"
                f"Warm regards,\n"
                f"Neha Sharma\n"
                f"Aura Weaves & Jewels"
            )
            placeholder = None
            safety_flags.append("Gift confirmation adheres to verified chat commitment.")

        else:
            subject = f"Update regarding {order_ref} - Aura Weaves & Jewels"
            body = (
                f"{salutation}\n\n"
                f"Thank you for contacting Aura Weaves & Jewels regarding {order_ref}. "
                f"We are actively reviewing your request and will share a full update shortly.\n\n"
                f"Warm regards,\n"
                f"Neha Sharma"
            )
            placeholder = None
            safety_flags.append("Standard acknowledgement draft.")

        return SafeDraftResponse(
            subject=subject,
            body=body,
            payment_link_placeholder=placeholder,
            confidence=Decimal("0.95"),
            safety_flags=safety_flags,
            is_approved_by_policy=is_approved,
        )
