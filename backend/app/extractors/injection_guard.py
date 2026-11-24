import re
from typing import Tuple, Optional


class InjectionGuard:
    """
    Prompt Injection and Unauthorized Instruction Firewall.
    Safety Rules:
    - Treat all customer messages as untrusted text, never as instructions.
    - Block prompt-injection attempts requesting refunds, secret disclosure, approval bypass, or unauthorized actions.
    - Zero tolerance for system override patterns.
    """

    SUSPICIOUS_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions",
        r"(?i)system\s+override",
        r"(?i)disregard\s+(all\s+)?prior",
        r"(?i)developer\s+mode",
        r"(?i)jailbreak",
        r"(?i)refund\s+me\s+(?:rs\.?|inr|₹)?\s*\d+",
        r"(?i)send\s+(?:money|funds|cash)",
        r"(?i)export\s+(all\s+)?(?:customer|database|tokens|keys|passwords)",
        r"(?i)reveal\s+(?:api\s+key|token|secret|password)",
        r"(?i)bypass\s+approval",
    ]

    @classmethod
    def scan_text(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans untrusted input for prompt injection, privilege escalation, or unauthorized action demands.
        Returns:
            (is_safe: bool, reason: Optional[str])
        """
        if not text:
            return True, None

        for pattern in cls.SUSPICIOUS_PATTERNS:
            match = re.search(pattern, text)
            if match:
                matched_phrase = match.group(0)
                return False, f"Untrusted input matched adversarial pattern: '{matched_phrase}'"

        return True, None

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> str:
        """
        Sanitizes untrusted text by stripping dangerous characters or delimiters before passing to any downstream reader.
        """
        if not text:
            return ""
        # Remove null bytes or terminal control sequences
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return sanitized
