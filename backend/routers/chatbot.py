"""
Chatbot API endpoints.

Provides a single endpoint for natural language queries about call analytics data.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.chatbot_service import AnalyticsChatbot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

# Global chatbot instance (singleton pattern for maintaining conversation state)
_chatbot_instance: Optional[AnalyticsChatbot] = None


def get_chatbot() -> AnalyticsChatbot:
    """Get or create the chatbot instance."""
    global _chatbot_instance

    if _chatbot_instance is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./db.db")
        # Check for both OpenRouter and Anthropic API keys
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="API key not configured. Please set OPENROUTER_API_KEY or ANTHROPIC_API_KEY in your environment."
            )

        _chatbot_instance = AnalyticsChatbot(database_url=database_url, api_key=api_key)
        logger.info("Chatbot instance created successfully")

    return _chatbot_instance


# Request/Response Schemas
class ChatRequest(BaseModel):
    """Request schema for chatbot endpoint."""

    message: str = Field(
        ...,
        description="User's natural language question or message",
        min_length=1,
        max_length=1000,
        examples=[
            "Hi!",
            "What's the average call time?",
            "Show me compliance failures from last week",
            "How many calls had objections yesterday?",
        ]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What's the average call time over the last 30 days?"
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chatbot endpoint."""

    response: str = Field(..., description="Natural language response from the assistant")
    sql_query: Optional[str] = Field(None, description="SQL query that was executed (if any)")
    is_greeting: bool = Field(False, description="Whether this was a greeting message")
    success: bool = Field(True, description="Whether the request was processed successfully")
    error: Optional[str] = Field(None, description="Error message if success is False")
    timestamp: str = Field(..., description="ISO timestamp of the response")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "The average call time over the last 30 days is 4 minutes and 12 seconds, based on 1,247 calls.",
                "sql_query": "SELECT AVG(call_duration_minutes) FROM call_records WHERE call_timestamp >= date('now', '-30 days')",
                "is_greeting": False,
                "success": True,
                "error": None,
                "timestamp": "2024-03-17T10:30:00Z"
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""

    history: List[Dict[str, Any]] = Field(..., description="List of conversation messages")
    total_messages: int = Field(..., description="Total number of messages in history")


# Endpoints
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the analytics chatbot.

    This is the main endpoint for interacting with the chatbot. You can:
    - Greet the bot: "Hi", "Hello"
    - Ask analytics questions: "What's the average call time?"
    - Request specific metrics: "Show me compliance failures from last week"
    - Explore trends: "What are the top objections this month?"

    The chatbot will:
    1. Understand your natural language question
    2. Generate appropriate SQL queries to fetch the data
    3. Execute queries safely (read-only)
    4. Format results in natural language with context and insights

    **Example questions:**
    - "What's the average call time?"
    - "How many calls failed compliance yesterday?"
    - "Show me the top 5 objections this week"
    - "Compare sentiment scores between morning and afternoon calls"
    """
    try:
        chatbot = get_chatbot()
        result = chatbot.chat(request.message)

        from datetime import datetime
        result["timestamp"] = datetime.now().isoformat()

        return ChatResponse(**result)

    except Exception as e:
        logger.exception(f"Error in chat endpoint: {e}")
        from datetime import datetime
        return ChatResponse(
            response="I apologize, but I'm experiencing technical difficulties. Please try again later.",
            sql_query=None,
            is_greeting=False,
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@router.get("/history", response_model=ConversationHistoryResponse)
async def get_history():
    """
    Get the conversation history.

    Returns all messages exchanged in the current session.
    """
    try:
        chatbot = get_chatbot()
        history = chatbot.get_conversation_history()

        return ConversationHistoryResponse(
            history=history,
            total_messages=len(history)
        )

    except Exception as e:
        logger.exception(f"Error retrieving history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        )


@router.post("/clear")
async def clear_history():
    """
    Clear the conversation history.

    Resets the chatbot's memory of the current conversation.
    """
    try:
        chatbot = get_chatbot()
        chatbot.clear_history()

        return {
            "success": True,
            "message": "Conversation history cleared successfully"
        }

    except Exception as e:
        logger.exception(f"Error clearing history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear conversation history"
        )


@router.get("/status")
async def chatbot_status():
    """
    Check chatbot service status.

    Returns information about the chatbot's configuration and availability.
    """
    try:
        # Check for both OpenRouter and Anthropic API keys
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        database_url = os.getenv("DATABASE_URL", "sqlite:///./db.db")

        has_api_key = bool(api_key)
        is_initialized = _chatbot_instance is not None

        status = "ready" if has_api_key else "not_configured"

        return {
            "status": status,
            "has_api_key": has_api_key,
            "is_initialized": is_initialized,
            "database_url": database_url.split("://")[0] + "://***",  # Hide credentials
            "message": "Chatbot is ready" if has_api_key else "API key not configured (set OPENROUTER_API_KEY or ANTHROPIC_API_KEY)"
        }

    except Exception as e:
        logger.exception(f"Error checking chatbot status: {e}")
        return {
            "status": "error",
            "has_api_key": False,
            "is_initialized": False,
            "message": str(e)
        }
