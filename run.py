"""
One command, whole system:  python run.py

  Reality -> Data -> Understanding -> Decision -> ACTION -> MEASURE -> LEARN -> repeat

Box 4 is the one the first two projects never had: the loop that finds out
whether the decision was any good, and updates itself.
"""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"

if not (ROOT / "data" / "raw" / "scanner_data.csv").exists():
    sys.exit(
        "\nMISSING DATA: data/raw/scanner_data.csv\n\n"
        "Download 'Retail Store Sales Transactions (Scanner Data)' from Kaggle:\n"
        "  https://www.kaggle.com/datasets/marian447/retail-store-sales-transactions\n"
        "unzip it, and place scanner_data.csv in data/raw/\n"
    )

STAGES = [
    ("Box 1   Data, unit price, COGS check, eligibility", "data.py"),
    ("Box 2   The demand curve — and why this data can't give one", "elasticity.py"),
    ("Box 3   The optimizer — and what it refuses to do", "optimize.py"),
    ("Box 4   THE CLOSED LOOP — act, observe, learn, re-optimise", "loop.py"),
    ("Box 5   Build the dashboard", "dashboard.py"),
]

for name, script in STAGES:
    print(f"\n{'=' * 76}\n  {name}\n{'=' * 76}")
    t = time.time()
    if subprocess.run([sys.executable, "-u", script], cwd=SRC).returncode != 0:
        sys.exit(f"\nFAILED at: {name}")
    print(f"  ...{time.time() - t:.1f}s")

print("\n\n" + "=" * 76)
print("  DONE.  Open docs/index.html in a browser.")
print("=" * 76)
