import uuid
from typing import Dict, Any
from app.config import settings


class RazorpayTestService:
    """
    Razorpay Test Mode / Sandbox Payment Link Service.
    Safety Rules:
    - Zero live payment credentials or live money.
    - Strictly Test Mode ('rzp_test_*').
    - Returns simulated sandbox payment link URL for demo purposes.
    """

    @classmethod
    def create_payment_link(cls, amount: float, currency: str, description: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        # Generate sandbox payment link id
        link_id = f"plink_test_{uuid.uuid4().hex[:12]}"
        short_url = f"https://rzp.io/i/test_{uuid.uuid4().hex[:8]}"

        return {
            "id": link_id,
            "entity": "payment_link",
            "amount": int(amount * 100),  # In paise
            "currency": currency or "INR",
            "status": "created",
            "short_url": short_url,
            "description": description,
            "customer": {
                "name": customer_info.get("name", "Valued Customer"),
                "contact": customer_info.get("contact", ""),
                "email": customer_info.get("email", ""),
            },
            "mode": "TEST_SANDBOX",
            "watermark": settings.DATASET_WATERMARK,
        }
