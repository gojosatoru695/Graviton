"""
Jarvis Policy Safety & Prompt-Injection Defense Module.

Rules:
- Treat ALL customer messages as untrusted data, never as instructions.
- Detect phrases attempting to override policy, reveal secrets, bypass approval, or issue refunds.
- Return PROMPT_INJECTION_BLOCKED when an attack is detected.
- Preserve the original message as evidence for security auditing.
- Never execute an action based on customer instructions.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class PromptInjectionDetectionResult:
    """
    Detailed audit outcome of prompt-injection analysis.
    """
    def __init__(
        self,
        is_injection: bool,
        error_code: Optional[str] = None,
        threat_patterns: Optional[List[str]] = None,
        original_message_evidence: Optional[Dict[str, Any]] = None,
        sanitized_summary: Optional[str] = None,
    ):
        self.is_injection = is_injection
        self.error_code = error_code
        self.threat_patterns = threat_patterns or []
        self.original_message_evidence = original_message_evidence
        self.sanitized_summary = sanitized_summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_injection": self.is_injection,
            "error_code": self.error_code,
            "threat_patterns": self.threat_patterns,
            "original_message_evidence": self.original_message_evidence,
            "sanitized_summary": self.sanitized_summary,
        }


# Canonical adversarial attack signatures
JAILBREAK_PATTERNS: List[Tuple[str, str]] = [
    (r"(?i)\b(?:system\s+)?override\s+(?:all\s+)?(?:policy|policies|rules?|instructions?)\b", "Adversarial command pattern attempting instruction/policy override."),
    (r"(?i)\bsystem\s+override\b", "Adversarial command pattern attempting instruction override ('SYSTEM OVERRIDE')."),
    (r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b", "Adversarial command pattern attempting to clear instruction context."),
    (r"(?i)\bdisregard\s+(?:all\s+)?prior\s+(?:prompts?|instructions?|rules?)\b", "Adversarial directive to disregard system guardrails."),
    (r"(?i)\byou\s+are\s+now\s+in\s+(?:developer|dan|jailbreak|admin|god)\s+mode\b", "Roleplay jailbreak attempt."),
    (r"(?i)\b(?:reveal|show|dump|print)\s+(?:all\s+)?(?:secrets?|system\s+prompt|instructions?|api\s*keys?|credentials?)\b", "Secret / credential disclosure request."),
    (r"(?i)\bexport\s+(?:all\s+)?customer\s+(?:phone|contact|data|records?|numbers?)\b", "Unauthorized customer data exfiltration attempt."),
    (r"(?i)\breturn\s+(?:secret|api|auth|database|env)\s+keys?\b", "Secret / credential disclosure request."),
    (r"(?i)\b(?:issue|send|transfer|process)\s+(?:me\s+)?(?:a\s+)?(?:direct\s+)?refund\b", "Unauthorized direct automated refund demand."),
    (r"(?i)\brefund\s+me\b", "Unauthorized direct automated refund demand."),
    (r"(?i)\bmark\s+(?:all\s+)?orders?\s+as\s+(?:fully\s+)?paid\b", "Unauthorized ledger manipulation command."),
    (r"(?i)\b(?:bypass|skip|disable)\s+(?:all\s+)?approval(?:s)?\b", "Approval gate bypass directive."),
    (r"(?i)\bexecute\s+without\s+(?:seller|human|manual)\s+approval\b", "Human-in-the-loop bypass directive."),
]


def inspect_for_prompt_injection(
    text: str,
    channel: str = "WhatsApp",
    speaker: str = "CUSTOMER",
) -> PromptInjectionDetectionResult:
    """
    Inspects customer text for prompt-injection attacks.
    Treats customer messages as strictly untrusted data.
    """
    if not text or not text.strip():
        return PromptInjectionDetectionResult(
            is_injection=False,
            sanitized_summary="Empty message text.",
        )

    matched_threats: List[str] = []

    for pattern, explanation in JAILBREAK_PATTERNS:
        if re.search(pattern, text):
            matched_threats.append(explanation)

    if matched_threats:
        # Create immutable cryptographic evidence snapshot of the attack
        msg_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        evidence_payload = {
            "evidence_type": "PROMPT_INJECTION_SECURITY_INCIDENT",
            "sha256": msg_sha,
            "source_channel": channel,
            "speaker": speaker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_text_quarantined": text,
            "threat_patterns_matched": matched_threats,
        }

        return PromptInjectionDetectionResult(
            is_injection=True,
            error_code="PROMPT_INJECTION_BLOCKED",
            threat_patterns=matched_threats,
            original_message_evidence=evidence_payload,
            sanitized_summary="[QUARANTINED: Prompt-injection attack neutralized. Zero action taken.]",
        )

    return PromptInjectionDetectionResult(
        is_injection=False,
        sanitized_summary="Message verified benign. No adversarial patterns detected.",
    )
