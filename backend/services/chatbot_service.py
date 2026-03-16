"""
Analytics Chatbot Service - Uses LangChain + Claude to answer natural language questions
about call analytics data by generating and executing SQL queries.
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlalchemy.orm import Session

from services.sql_safety import validate_sql, SQLSafetyError

logger = logging.getLogger(__name__)


# System prompt for the senior data analytics assistant
ANALYTICS_SYSTEM_PROMPT = """You are a senior data analytics assistant specializing in call center analytics. 
also you are an empathetic customer service representative named Alex, who speaks in a friendly, concise, and conversational manner.
In the prompt, encourage the use of appropriate emojis and natural, conversational language to boost rapport.
Your role is to help users understand their call data by answering questions about:
- Call performance metrics (average call time, success rates, etc.)
- Agent performance and trends
- Compliance violations and patterns
- Customer sentiment analysis
- Objection handling and patterns
- Promise-to-pay analysis
- Time-based trends and patterns

**Database Schema:**
You have access to a table called `call_records` with the following columns:

**Core Call Information:**
- id: Unique call identifier (INTEGER)
- dealer_id: Dealer/agent identifier (STRING)
- call_timestamp: When the call occurred (DATETIME)
- call_duration_minutes: Length of call in minutes (FLOAT)
- time_of_day_category: Morning/Afternoon/Evening (STRING)

**Call Outcomes:**
- call_outcome: Overall outcome (STRING)
- intent_class: Customer intent category (STRING)
- confidence: Confidence score for intent (FLOAT 0-1)
- next_action: Recommended next step (STRING)
- decision_rationale: Explanation for the decision (STRING)

**Financial Data:**
- days_past_due: Days account is overdue (INTEGER)
- debt_balance: Total amount owed (FLOAT)
- promise_amount: Amount customer promised to pay (FLOAT)
- promise_coverage_ratio: Ratio of promise to total debt (FLOAT)
- delta_aging_bucket: Age category of debt (STRING)
- fulfillment_probability: Likelihood of payment (FLOAT 0-1)

**Compliance:**
- compliance_status: PASS or FAIL (STRING)
- compliance_violations: Comma-separated violation codes (STRING)
- compliance_details: Detailed compliance information (STRING)

**Sentiment & Quality:**
- sentiment_score: Customer sentiment (-1 to 1, higher is better) (FLOAT)
- transcript_summary: Summary of the call (STRING)

**Objections:**
- primary_objection: Main customer objection (STRING)
- all_objections: Comma-separated list of all objections (STRING)
- objection_details: Detailed objection information (STRING)
- objection_confidence: Confidence in objection detection (FLOAT 0-1)

**Flags:**
- dispute_flag: Whether customer disputed the debt (BOOLEAN)
- created_at: When record was created (DATETIME)

**Your behavior:**
1. When users greet you (hi, hello, hey), respond warmly and introduce yourself
2. For analytics questions, write SQL queries to extract the needed data
3. Format numbers clearly (e.g., "3 minutes 45 seconds" instead of "3.75")
4. Be conversational and friendly and maintain more human like conversation and tone, but professional
5. If a question is unclear, ask for clarification
6. ONLY use SELECT queries - never modify data
7. **IMPORTANT: Always provide SUMMARIES, not detailed logs**
   - For compliance/status checks: Show totals and counts (e.g., "5 calls: 3 passed, 2 failed")
   - For lists: Aggregate and summarize rather than listing individual items
   - Only show detailed breakdowns if specifically asked (e.g., "show me each call")
   - Use conversational summaries: "Out of 5 recent calls, 3 met compliance standards and 2 had issues"

**Example interactions:**
- "Hi!" → "Hello! I'm your senior data analytics assistant. I can help you analyze your call center data - performance metrics, compliance issues, customer sentiment, and more. What would you like to know?"
- "What's the average call time?" → Generate SQL, then: "The average call time over the last 30 days is 4 minutes and 12 seconds"
- "Show me compliance for last 5 calls" → Generate SQL, then: "Out of the last 5 calls, 3 passed compliance checks and 2 failed. Would you like details on the failures?"
- "Show compliance status" → Provide summary counts, not individual call logs

Current date: {current_date}

Remember: Be helpful, insightful, and conversational. You're not just running queries - you're a senior analyst helping stakeholders understand their data.
"""


class AnalyticsChatbot:
    """Chatbot that answers natural language questions about call analytics data."""

    def __init__(self, database_url: str, api_key: str = None):
        """
        Initialize the chatbot with database connection and OpenRouter API.

        Args:
            database_url: SQLAlchemy database URL
            api_key: OpenRouter API key (defaults to env var OPENROUTER_API_KEY or ANTHROPIC_API_KEY)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY or ANTHROPIC_API_KEY must be provided or set in environment")

        # Initialize the database connection
        self.db = SQLDatabase.from_uri(database_url)

        # Initialize Claude LLM via OpenRouter
        self.llm = ChatOpenAI(
            model="openai/o3-mini",
            openai_api_key=self.api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.5,  # More deterministic for SQL generation
            max_tokens=512,  # Reasonable limit for most responses (saves credits!)
        )

        # Create the SQL toolkit and agent
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)

        # Format the system prompt with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        formatted_prompt = ANALYTICS_SYSTEM_PROMPT.format(current_date=current_date)

        # Create the SQL agent with our custom prompt
        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type="openai-tools",
            verbose=True,
            prefix=formatted_prompt,
            max_iterations=5,
            max_execution_time=30,
        )

        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []

        logger.info("AnalyticsChatbot initialized successfully")

    def _is_greeting(self, message: str) -> bool:
        """Check if the message is a greeting."""
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy"]
        message_lower = message.lower().strip()
        return any(greeting in message_lower for greeting in greetings)

    def _handle_greeting(self) -> str:
        """Generate a greeting response."""
        return (
            "Hello! I'm your senior data analytics assistant for call center analytics. "
            "I can help you understand your call data - metrics like average call times, "
            "success rates, compliance issues, customer sentiment, objection patterns, and much more. "
            "\n\nWhat would you like to know about your call data?"
        )

    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return a response.

        Args:
            user_message: The user's question or message

        Returns:
            Dictionary with response, SQL query (if any), and metadata
        """
        try:
            logger.info(f"User message: {user_message}")

            # Handle greetings separately
            if self._is_greeting(user_message) and len(self.conversation_history) == 0:
                response = self._handle_greeting()
                self.conversation_history.append({
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.now().isoformat()
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })

                return {
                    "response": response,
                    "sql_query": None,
                    "is_greeting": True,
                    "success": True,
                }

            # Process analytics question through the agent
            result = self.agent.invoke({"input": user_message})

            # Extract the response
            response = result.get("output", "I'm sorry, I couldn't process that request.")

            # Try to extract SQL from intermediate steps (if available)
            sql_query = None
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                if len(step) >= 2:
                    action = step[0]
                    if hasattr(action, 'tool_input'):
                        # The SQL query is in the tool input
                        potential_sql = action.tool_input
                        if isinstance(potential_sql, str) and potential_sql.strip().upper().startswith('SELECT'):
                            try:
                                # Validate the SQL before storing it
                                sql_query = validate_sql(potential_sql)
                                break
                            except SQLSafetyError:
                                logger.warning(f"Generated SQL failed safety check: {potential_sql}")
                                continue

            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "sql_query": sql_query,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"Successfully processed query. SQL: {sql_query is not None}")

            return {
                "response": response,
                "sql_query": sql_query,
                "is_greeting": False,
                "success": True,
            }

        except Exception as e:
            logger.exception(f"Error processing chatbot message: {e}")
            error_msg = (
                "I apologize, but I encountered an error processing your request. "
                "Please try rephrasing your question or contact support if the issue persists."
            )

            return {
                "response": error_msg,
                "sql_query": None,
                "is_greeting": False,
                "success": False,
                "error": str(e),
            }

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the full conversation history."""
        return self.conversation_history

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
