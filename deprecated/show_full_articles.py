#!/usr/bin/env python3
import json
from pathlib import Path

def get_article_text(chunks, article_id: str) -> str:
    parts = [ch for ch in chunks if ch.get('metadata', {}).get('article') == article_id]
    # sort by chunk_index if present
    parts.sort(key=lambda ch: ch.get('metadata', {}).get('chunk_index', 0))
    return "\n".join(ch.get('content', '') for ch in parts)

def main() -> None:
    data_path = Path('processed_chunks.json')
    if not data_path.exists():
        print('processed_chunks.json not found')
        return
    chunks = json.loads(data_path.read_text(encoding='utf-8'))

    for art in ['1', '2']:
        full_text = get_article_text(chunks, art)
        out_path = Path(f'Article_{art}_full.txt')
        out_path.write_text(full_text, encoding='utf-8')
        print(f"===== ARTICLE {art} (saved to {out_path}) =====")
        print(full_text)
        print()

if __name__ == '__main__':
    main()

