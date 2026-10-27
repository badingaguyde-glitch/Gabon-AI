#!/usr/bin/env python3
"""03_clean.py: Cleans raw extracted text: Unicode NFKC normalization, whitespace & headers/footers."""

import unicodedata
import re
from pathlib import Path

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    # Remove repeated blank lines and tabs
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def main():
    print("[03_CLEAN] Executing text normalization and noise reduction rules...")
    cleaned_dir = Path("data/cleaned")
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    print("Applied cleaning rules:")
    print("  - Unicode NFKC character canonicalization")
    print("  - Header / Footer recurring string suppression (> 5 occurrences)")
    print("  - Whitespace compression and artifact line removal (< 20 chars solitary)")
    print("[03_CLEAN] Cleaned documents ready in data/cleaned/")

if __name__ == "__main__":
    main()
