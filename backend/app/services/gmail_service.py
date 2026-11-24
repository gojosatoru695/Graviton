import uuid
from typing import Dict, Any
from app.config import settings


class GmailDraftService:
    """
    Gmail Draft & Simulated Delivery Service.
    Safety Rules:
    - Never sends real emails or real SMS messages.
    - Creates email drafts or simulated outbound delivery records.
    """

    @classmethod
    def create_draft(cls, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        draft_id = f"draft_{uuid.uuid4().hex[:12]}"
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        return {
            "draft_id": draft_id,
            "message_id": message_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "DRAFT_SAVED",
            "simulated": True,
            "outbound_sent": False,  # Strict guarantee: never sent
            "watermark": settings.DATASET_WATERMARK,
        }
