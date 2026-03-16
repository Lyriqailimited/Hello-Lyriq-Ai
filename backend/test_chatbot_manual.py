"""
Manual testing script for the Analytics Chatbot.

This script allows you to test the chatbot interactively from the command line.

Usage:
    python test_chatbot_manual.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.chatbot_service import AnalyticsChatbot
from services.sql_safety import SQLValidator


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def test_sql_validator():
    """Test the SQL validator with sample queries."""
    print("🔒 Testing SQL Safety Validator...")
    print_separator()

    test_cases = [
        ("Valid SELECT", "SELECT * FROM call_records LIMIT 10", True),
        ("Valid SELECT with WHERE", "SELECT AVG(call_duration_minutes) FROM call_records WHERE call_timestamp >= date('now', '-30 days')", True),
        ("Dangerous DELETE", "DELETE FROM call_records", False),
        ("Dangerous UPDATE", "UPDATE call_records SET dealer_id = 'X'", False),
        ("Dangerous DROP", "DROP TABLE call_records", False),
        ("Multiple statements", "SELECT * FROM call_records; DROP TABLE call_records;", False),
    ]

    for name, query, should_pass in test_cases:
        is_safe, reason = SQLValidator.is_safe_query(query)
        status = "✅ PASS" if is_safe == should_pass else "❌ FAIL"
        print(f"{status} | {name}")
        print(f"   Query: {query[:60]}...")
        print(f"   Result: {'Safe' if is_safe else 'Unsafe'} - {reason}")
        print()

    print_separator()


def test_chatbot_interactive():
    """Test the chatbot in interactive mode."""
    print("🤖 Analytics Chatbot - Interactive Testing")
    print_separator()

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not set in environment!")
        print("Please set your API key in the .env file:")
        print("   ANTHROPIC_API_KEY=your-api-key-here")
        return

    database_url = os.getenv("DATABASE_URL", "sqlite:///./db.db")

    try:
        print("Initializing chatbot...")
        chatbot = AnalyticsChatbot(database_url=database_url, api_key=api_key)
        print("✅ Chatbot initialized successfully!\n")

        # Test cases
        test_messages = [
            "Hi!",
            "What's the average call time?",
            "How many calls failed compliance in the last 7 days?",
            "Show me the top 5 objections this month",
        ]

        print("Running automated test queries...\n")
        for i, message in enumerate(test_messages, 1):
            print(f"Test {i}/{len(test_messages)}")
            print(f"📝 User: {message}")
            print()

            result = chatbot.chat(message)

            print(f"🤖 Assistant: {result['response']}")
            print()

            if result.get('sql_query'):
                print(f"💾 SQL Query:")
                print(f"   {result['sql_query']}")
                print()

            if not result['success']:
                print(f"⚠️  Error: {result.get('error')}")
                print()

            print_separator()

        # Interactive mode
        print("\n🎮 Entering interactive mode (type 'exit' to quit)...\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nGoodbye! 👋\n")
                    break

                result = chatbot.chat(user_input)

                print(f"\nAssistant: {result['response']}\n")

                if result.get('sql_query'):
                    print(f"SQL Query: {result['sql_query']}\n")

                if not result['success']:
                    print(f"Error: {result.get('error')}\n")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")

    except Exception as e:
        print(f"❌ Failed to initialize chatbot: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print(" " * 20 + "MARCO ANALYTICS CHATBOT - TESTING")
    print("=" * 80 + "\n")

    # Test SQL validator
    test_sql_validator()

    # Test chatbot
    test_chatbot_interactive()


if __name__ == "__main__":
    main()
