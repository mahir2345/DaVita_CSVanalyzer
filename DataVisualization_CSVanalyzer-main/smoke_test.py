import numpy as np
import pandas as pd

from main import compute_correlation_insights, handle_missing_values


def make_dataset(n=80, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    y = 2 * x + rng.normal(scale=0.2, size=n)  # strong positive correlation
    z = -1.5 * x + rng.normal(scale=0.3, size=n)  # strong negative correlation
    cat = rng.choice(["A", "B", "C"], size=n).astype(object)

    # add missing values
    x[::10] = np.nan
    cat[::15] = None

    return pd.DataFrame({"x": x, "y": y, "z": z, "category": cat})


def main():
    df = make_dataset()
    assert int(df.isnull().sum().sum()) > 0, "Dataset should contain missing values"

    processed, report = handle_missing_values(df, "auto")
    assert int(processed.isnull().sum().sum()) == 0, "Auto strategy should eliminate missing values"
    assert report["strategy_used"] in {"mean", "median", "mode", "ffill", "bfill"}, "Unexpected auto strategy"

    insights = compute_correlation_insights(processed, top_n=5, threshold=0.3)
    assert len(insights) > 0, "Should produce at least one correlation insight"

    # Ensure we find at least one strong relationship involving x
    pairs = {i["pair"] for i in insights}
    assert any("x vs y" in p or "x vs z" in p or "y vs x" in p or "z vs x" in p for p in pairs), (
        "Expected a top correlation involving x"
    )

    print("SMOKE TEST PASSED")
    print("Null handling:", report["strategy_used"], "-", report["reason"])
    print("Top correlations:")
    for item in insights:
        print(f"- {item['pair']}: {item['value']} ({item['direction']}, {item['strength']})")


if __name__ == "__main__":
    main()


