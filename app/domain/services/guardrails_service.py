
import re

class GuardrailsService:
    def __init__(self):
        # Regex Patterns
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(\+90|0)?\s*[0-9]{3}\s*[0-9]{3}\s*[0-9]{2}\s*[0-9]{2}\b', # TR Phone
            "credit_card": r'\b(?:\d{4}[-\s]){3}\d{4}\b',
            "tc_kimlik": r'\b[1-9]{1}[0-9]{10}\b' # Simply 11 digits starting with non-zero
        }

    def sanitize_text(self, text: str) -> str:
        if not text:
            return text
        
        sanitized = text
        for ptype, pattern in self.patterns.items():
            sanitized = re.sub(pattern, f"[REDACTED_{ptype.upper()}]", sanitized)
        
        return sanitized

    def sanitize_payload(self, payload: dict) -> dict:
        """
        Recursively sanitize strings in a dictionary.
        """
        new_payload = {}
        for k, v in payload.items():
            if isinstance(v, str):
                new_payload[k] = self.sanitize_text(v)
            elif isinstance(v, dict):
                new_payload[k] = self.sanitize_payload(v)
            elif isinstance(v, list):
                new_payload[k] = [
                    self.sanitize_payload(i) if isinstance(i, dict) else (self.sanitize_text(i) if isinstance(i, str) else i)
                    for i in v
                ]
            else:
                new_payload[k] = v
        return new_payload

guardrails = GuardrailsService()
