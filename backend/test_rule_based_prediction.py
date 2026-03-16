"""
Verification script for the enhanced rule-based fulfillment prediction.
Demonstrates how different feature combinations affect the prediction score.
"""

from ml.model import predict_fulfillment


def test_scenario(name: str, record: dict):
    """Test a scenario and print the results."""
    probability = predict_fulfillment(record)
    print(f"\n{name}")
    print(f"  Input: {record}")
    print(f"  → Fulfillment Probability: {probability:.4f}")


if __name__ == "__main__":
    print("=" * 80)
    print("RULE-BASED FULFILLMENT PREDICTION TEST SCENARIOS")
    print("=" * 80)

    # Scenario 1: High probability - committed intent, positive sentiment
    test_scenario(
        "Scenario 1: Best Case (Committed + High Sentiment + Recent)",
        {
            "intent_class": "COMMITTED",
            "sentiment_score": 0.9,
            "days_past_due": 15,
            "promise_coverage_ratio": 0.8,
            "call_duration_minutes": 6.5,
            "dispute_flag": False
        }
    )

    # Scenario 2: Medium probability - conditional intent
    test_scenario(
        "Scenario 2: Medium Case (Conditional Intent)",
        {
            "intent_class": "CONDITIONAL",
            "sentiment_score": 0.6,
            "days_past_due": 45,
            "promise_coverage_ratio": 0.5,
            "call_duration_minutes": 3.2,
            "dispute_flag": False
        }
    )

    # Scenario 3: Low probability - evasive intent
    test_scenario(
        "Scenario 3: Low Case (Evasive Intent + Low Sentiment)",
        {
            "intent_class": "EVASIVE",
            "sentiment_score": 0.2,
            "days_past_due": 120,
            "promise_coverage_ratio": 0.1,
            "call_duration_minutes": 1.5,
            "dispute_flag": False
        }
    )

    # Scenario 4: Dispute flag impact
    test_scenario(
        "Scenario 4: Dispute Flag Impact (Good metrics but dispute)",
        {
            "intent_class": "COMMITTED",
            "sentiment_score": 0.8,
            "days_past_due": 20,
            "promise_coverage_ratio": 0.7,
            "call_duration_minutes": 5.0,
            "dispute_flag": True  # This should reduce probability significantly
        }
    )

    # Scenario 5: Days past due impact
    test_scenario(
        "Scenario 5: Very Old Debt (90+ days)",
        {
            "intent_class": "COMMITTED",
            "sentiment_score": 0.7,
            "days_past_due": 150,
            "promise_coverage_ratio": 0.6,
            "call_duration_minutes": 4.0,
            "dispute_flag": False
        }
    )

    # Scenario 6: Short call duration
    test_scenario(
        "Scenario 6: Very Short Call (< 2 minutes)",
        {
            "intent_class": "COMMITTED",
            "sentiment_score": 0.7,
            "days_past_due": 30,
            "promise_coverage_ratio": 0.6,
            "call_duration_minutes": 1.0,  # Short call gets 0 points
            "dispute_flag": False
        }
    )

    # Scenario 7: High coverage ratio
    test_scenario(
        "Scenario 7: Full Coverage Promise (100%+)",
        {
            "intent_class": "COMMITTED",
            "sentiment_score": 0.8,
            "days_past_due": 25,
            "promise_coverage_ratio": 1.2,  # Promising more than owed (capped at 1.0)
            "call_duration_minutes": 7.0,
            "dispute_flag": False
        }
    )

    # Scenario 8: Missing fields (defaults)
    test_scenario(
        "Scenario 8: Missing Fields (All Defaults)",
        {}
    )

    print("\n" + "=" * 80)
    print("SCORING BREAKDOWN:")
    print("  - Intent: COMMITTED=0.40, CONDITIONAL=0.20, EVASIVE=0.0")
    print("  - Sentiment: score × 0.25")
    print("  - Days Past Due: 0-30=0.20, 31-60=0.15, 61-90=0.10, 90+=0.05")
    print("  - Promise Coverage: ratio × 0.30 (capped at 1.0)")
    print("  - Call Duration: <2min=0.0, 2-5min=0.05, 5+min=0.10")
    print("  - Dispute Penalty: -0.30")
    print("=" * 80)
