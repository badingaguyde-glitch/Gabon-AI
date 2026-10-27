#!/usr/bin/env python3
"""08_statistics.py: Generates quantitative pipeline reports and summary tables."""

import json
from pathlib import Path

def main():
    print("[08_STATISTICS] Generating consolidated dataset statistics...")
    train_p = Path("data/final/train.jsonl")
    val_p = Path("data/final/validation.jsonl")
    test_p = Path("data/final/test.jsonl")
    inst_p = Path("data/final/instruction_v1.0.jsonl")

    def read_docs(p):
        if not p.exists(): return []
        with open(p, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    train_docs = read_docs(train_p)
    val_docs = read_docs(val_p)
    test_docs = read_docs(test_p)
    inst_docs = read_docs(inst_p)

    all_corpus = train_docs + val_docs + test_docs
    total_tokens = sum(d.get("token_count", 0) for d in all_corpus)
    total_chars = sum(d.get("char_count", 0) for d in all_corpus)

    subtopics = {}
    for d in all_corpus:
        sub = d.get("subtopic", "general")
        subtopics[sub] = subtopics.get(sub, 0) + 1

    print("\n" + "="*50)
    print("DOMAIN CORPUS v1.0 SUMMARY")
    print("="*50)
    print(f"Total Documents:     {len(all_corpus):,}")
    print(f"Total Tokens:        {total_tokens:,}")
    print(f"Total Characters:    {total_chars:,}")
    print(f"Subtopics Breakdown: {subtopics}")
    print("\n" + "="*50)
    print("INSTRUCTION DATASET v1.0 SUMMARY")
    print("="*50)
    print(f"Total Instructions:  {len(inst_docs):,}")
    task_types = {}
    for inst in inst_docs:
        tt = inst.get("task_type", "general")
        task_types[tt] = task_types.get(tt, 0) + 1
    print(f"Task Types Breakdown:")
    for tt, cnt in sorted(task_types.items(), key=lambda x: -x[1]):
        print(f"  - {tt:<25}: {cnt} ({cnt/max(1,len(inst_docs))*100:.1f}%)")
    print("="*50)
    print("[08_STATISTICS] Statistics generation complete.")

if __name__ == "__main__":
    main()
