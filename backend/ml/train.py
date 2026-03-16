"""
One-time training script – generates a synthetic dataset and trains an
XGBoost classifier to predict promise_fulfilled.

Run:  python -m ml.train
Outputs: ml/xgb_model.pkl
"""

import os
import pickle

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split

SEED = 42
N_SAMPLES = 100
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "xgb_model.pkl")


def generate_synthetic_data(n: int = N_SAMPLES) -> pd.DataFrame:
    """Create synthetic training data with realistic distributions."""
    rng = np.random.default_rng(SEED)
    return pd.DataFrame(
        {
            "sentiment_score": rng.uniform(0.0, 1.0, n),
            "days_past_due": rng.integers(0, 180, n),
            "promise_coverage_ratio": rng.uniform(0.0, 1.0, n),
            "call_duration_minutes": rng.uniform(1.0, 30.0, n),
            "intent_encoded": rng.choice([0, 1, 2], n),
            "promise_fulfilled": rng.choice([0, 1], n, p=[0.4, 0.6]),
        }
    )


def main():
    df = generate_synthetic_data()
    X = df.drop(columns=["promise_fulfilled"])
    y = df["promise_fulfilled"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED
    )

    model = XGBClassifier(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        random_state=SEED,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)
    print(f"Test accuracy: {acc:.2%}")

    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
