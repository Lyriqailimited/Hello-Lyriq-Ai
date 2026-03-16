"""
PII token map – replaces sensitive values with anonymous tokens.
In production this would be backed by a secure vault; here we use a static dict.
"""

TOKEN_MAP: dict[str, str] = {
    "Jane Smith": "CRT-8972p",
    "John Doe": "CRT-4431q",
    "Maria Garcia": "CRT-5523r",
    "Robert Chen": "CRT-6614s",
    "Aisha Patel": "CRT-7705t",
}


def anonymise(value: str) -> str:
    """Replace known PII strings with their anonymous tokens."""
    result = value
    for original, token in TOKEN_MAP.items():
        result = result.replace(original, token)
    return result
