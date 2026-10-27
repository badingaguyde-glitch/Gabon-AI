#!/usr/bin/env python3
"""07_token_count.py: Measures token distribution using standard BPE / Qwen tokenizer family."""

import json
from pathlib import Path

def main():
    print("[07_TOKEN_COUNT] Calculating corpus token metrics (Qwen/Qwen2.5-7B tokenizer profile)...")
    train_file = Path("data/final/train.jsonl")
    if not train_file.exists():
        print("data/final/train.jsonl not found.")
        return

    tokens = []
    chars = []
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            tokens.append(d.get("token_count", 0))
            chars.append(d.get("char_count", 0))

    tokens.sort()
    total_tokens = sum(tokens)
    total_chars = sum(chars)
    n = len(tokens)
    
    min_t = tokens[0] if tokens else 0
    med_t = tokens[n // 2] if tokens else 0
    avg_t = total_tokens / max(1, n)
    p95_t = tokens[int(n * 0.95)] if tokens else 0
    max_t = tokens[-1] if tokens else 0

    print("Token statistics for Train Corpus:")
    print(f"  - Total documents : {n:,}")
    print(f"  - Total tokens    : {total_tokens:,}")
    print(f"  - Total characters: {total_chars:,}")
    print(f"  - Min tokens/doc  : {min_t}")
    print(f"  - Median tokens   : {med_t}")
    print(f"  - Average tokens  : {avg_t:.1f}")
    print(f"  - 95th percentile : {p95_t}")
    print(f"  - Max tokens/doc  : {max_t}")
    print("[07_TOKEN_COUNT] Token analysis complete.")

if __name__ == "__main__":
    main()
