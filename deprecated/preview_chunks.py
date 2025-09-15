#!/usr/bin/env python3
import json
import re

def main() -> None:
    try:
        with open('processed_chunks.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
    except Exception as e:
        print(f"Error reading processed_chunks.json: {e}")
        return

    def preview(text: str, n: int = 200) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text[:n] + ("..." if len(text) > n else "")

    count = min(5, len(chunks))
    for i in range(count):
        ch = chunks[i]
        meta = ch.get('metadata', {})
        print(f"ID: {ch.get('id', 'N/A')}")
        print(f"Article: {meta.get('article', meta.get('regulation_number', 'N/A'))}  Tokens: {meta.get('tokens', 'N/A')}")
        print(f"Preview: {preview(ch.get('content', ''))}")
        print()

if __name__ == '__main__':
    main()

