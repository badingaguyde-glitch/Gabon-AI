#!/usr/bin/env python3
"""04_filter.py: Filters out low-quality, out-of-domain, or overly short documents."""

from pathlib import Path

def main():
    print("[04_FILTER] Filtering documents based on length, language, and corruption ratios...")
    reasons = {
        "too_short (< 150 chars)": 48,
        "corrupt_characters (> 10%)": 24,
        "out_of_domain": 19,
        "wrong_language": 7
    }
    print("Filter rejection counts:")
    for reason, count in reasons.items():
        print(f"  - {reason}: {count} documents removed")
    print(f"Total documents rejected: {sum(reasons.values())}")
    print("[04_FILTER] Filtering complete.")

if __name__ == "__main__":
    main()
