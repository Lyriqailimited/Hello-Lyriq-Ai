"""
Intent classification service using Claude API via LangChain.

Classifies a call transcript summary into one of:
  - COMMITTED   (debtor agreed to pay)
  - CONDITIONAL (debtor expressed conditional willingness)
  - EVASIVE     (debtor avoided commitment)

Returns {"intent_class": str, "confidence": float}.

Uses Claude API via LangChain structured output when ANTHROPIC_API_KEY is set,
falls back to keyword-based classification otherwise.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Keyword-based classifier fallback
_COMMITTED_KEYWORDS = ["will pay", "agree", "committed", "promise to pay", "i can pay"]
_CONDITIONAL_KEYWORDS = ["maybe", "if", "possibly", "might", "consider", "depends"]
_EVASIVE_KEYWORDS = [
    "cannot",
    "refuse",
    "not able",
    "won't",
    "don't have",
    "no money",
    "dispute",
]

# LangChain imports (only if API key is available)
_claude_chain = None


def _init_claude_chain():
    """Initialize the Claude API chain with LangChain structured output."""
    global _claude_chain

    if _claude_chain is not None:
        return _claude_chain

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.pydantic_v1 import BaseModel, Field

        # Structured output schema
        class IntentClassification(BaseModel):
            """Intent classification result."""
            intent_class: str = Field(
                description="The classified intent: COMMITTED, CONDITIONAL, or EVASIVE"
            )
            confidence: float = Field(
                description="Confidence score between 0 and 1"
            )
            reasoning: str = Field(
                description="Brief explanation for the classification"
            )

        # Prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing debt collection call transcripts.

Classify the debtor's intent into one of three categories:

1. COMMITTED - The debtor clearly agreed to pay or made a firm commitment
   Examples: "I will pay $500 by Friday", "I agree to the payment plan", "I promise to pay"

2. CONDITIONAL - The debtor expressed willingness but with conditions or uncertainty
   Examples: "Maybe I can pay next week", "If I get my paycheck, I'll send something", "I might be able to pay"

3. EVASIVE - The debtor refused, avoided commitment, or was uncooperative
   Examples: "I refuse to pay", "I can't pay anything", "I won't discuss this", "I dispute this debt"

Provide a confidence score between 0 and 1 based on how clear the intent is in the transcript.
"""),
            ("user", "Classify the intent in this call transcript summary:\n\n{transcript_summary}")
        ])

        # Create the chain with structured output
        llm = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0,
            api_key=api_key
        )

        _claude_chain = prompt | llm.with_structured_output(IntentClassification)
        logger.info("Claude API chain initialized successfully (model: claude-3-5-haiku)")
        return _claude_chain

    except Exception as e:
        logger.warning("Failed to initialize Claude API chain: %s", e)
        return None


def _classify_via_claude_api(summary: str) -> dict[str, Any]:
    """Classify intent using Claude API via LangChain."""
    chain = _init_claude_chain()
    if chain is None:
        raise Exception("Claude chain not initialized")

    result = chain.invoke({"transcript_summary": summary})

    # Normalize intent_class to uppercase
    intent_class = result.intent_class.upper()

    # Validate intent_class
    if intent_class not in ["COMMITTED", "CONDITIONAL", "EVASIVE"]:
        logger.warning(
            "Claude returned invalid intent '%s', defaulting to CONDITIONAL",
            intent_class
        )
        intent_class = "CONDITIONAL"

    # Clamp confidence to [0, 1]
    confidence = max(0.0, min(1.0, result.confidence))

    logger.info(
        "Claude API classification: %s (confidence=%.4f) — %s",
        intent_class,
        confidence,
        result.reasoning
    )

    return {
        "intent_class": intent_class,
        "confidence": round(confidence, 4)
    }


def _classify_via_keywords(summary: str) -> dict[str, Any]:
    """Fallback keyword-based classification."""
    text = summary.lower()

    for kw in _COMMITTED_KEYWORDS:
        if kw in text:
            logger.info("Intent classified: COMMITTED (keyword=%r, confidence=0.70)", kw)
            return {"intent_class": "COMMITTED", "confidence": 0.70}

    for kw in _EVASIVE_KEYWORDS:
        if kw in text:
            logger.info("Intent classified: EVASIVE (keyword=%r, confidence=0.65)", kw)
            return {"intent_class": "EVASIVE", "confidence": 0.65}

    for kw in _CONDITIONAL_KEYWORDS:
        if kw in text:
            logger.info("Intent classified: CONDITIONAL (keyword=%r, confidence=0.60)", kw)
            return {"intent_class": "CONDITIONAL", "confidence": 0.60}

    logger.info("Intent classified: CONDITIONAL (no keyword match, confidence=0.50)")
    return {"intent_class": "CONDITIONAL", "confidence": 0.50}


def classify_intent(summary: str) -> dict[str, Any]:
    """
    Classify the intent from a transcript summary string.

    Attempts Claude API first (if ANTHROPIC_API_KEY is set),
    falls back to keyword-based classification on error or missing key.
    """
    # Try Claude API first
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return _classify_via_claude_api(summary)
        except Exception as e:
            logger.error("Claude API failed: %s, falling back to keyword classification", e)
    else:
        logger.debug("No ANTHROPIC_API_KEY found, using keyword-based classification")

    # Fallback to keywords
    return _classify_via_keywords(summary)


def is_claude_api_available() -> bool:
    """Check if Claude API is configured and available."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))