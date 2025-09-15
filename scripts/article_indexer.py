import json
import os
from typing import List, Dict, Any


def extract_articles(full_text: str) -> List[Dict[str, Any]]:
    # Reuse the robust article extraction in doc_processor
    from doc_processor import DocumentProcessor

    processor = DocumentProcessor()
    return processor._extract_articles(full_text)  # noqa: SLF001 intentional private access


def build_full_article_entries(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create one vector entry per article containing the full article text."""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = None

    entries: List[Dict[str, Any]] = []
    for art in articles:
        article_id = str(art.get("article", "")).strip()
        content = art.get("content", "")
        token_count = len(encoding.encode(content)) if encoding else len(content.split())

        entries.append({
            "id": f"article_{article_id}_full",
            "content": content,
            "metadata": {
                "article": article_id,
                "page": art.get("page"),
                "position": art.get("position"),
                "chunk_index": 0,
                "total_chunks": 1,
                "tokens": token_count,
                "citation": f"Commercial Code (Cap. 13) Art. {article_id}",
            },
        })

    return entries


def main() -> None:
    source_path = "malta_commercial_code_text.txt"
    output_path = "processed_chunks.json"

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Could not find {source_path}")

    with open(source_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    articles = extract_articles(full_text)
    entries = build_full_article_entries(articles)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)

    print(f"Wrote {len(entries)} full-article entries to {output_path}")


if __name__ == "__main__":
    main()


