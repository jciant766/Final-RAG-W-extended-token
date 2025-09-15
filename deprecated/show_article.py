C:\Users\Jake\Desktop\Final RAG W extended token\ocr\outputimport argparse
import os
from typing import Dict, Any, List


def extract_articles(full_text: str) -> List[Dict[str, Any]]:
    # Reuse existing article extraction for consistency
    from doc_processor import DocumentProcessor

    processor = DocumentProcessor()
    return processor._extract_articles(full_text)  # noqa: SLF001 (intentional private use)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print full text of a Malta Commercial Code article")
    parser.add_argument("--path", default="malta_commercial_code_text.txt", help="Path to statute text file")
    parser.add_argument("--article", required=False, help="Article identifier (e.g., 1, 26A, 477)")
    parser.add_argument("--list", action="store_true", help="List available article IDs and exit")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        raise FileNotFoundError(f"Statute text not found at {args.path}")

    with open(args.path, "r", encoding="utf-8") as f:
        text = f.read()

    articles = extract_articles(text)

    if args.list:
        print("Available articles (first 50 shown):")
        for a in articles[:50]:
            print(a["article"])
        if len(articles) > 50:
            print(f"... and {len(articles) - 50} more")
        return

    if not args.article:
        raise SystemExit("Please provide --article or use --list to see available IDs")

    target = str(args.article).upper()
    match = next((a for a in articles if str(a.get("article", "")).upper() == target), None)
    if not match:
        raise SystemExit(f"Article {target} not found. Try --list to see available IDs.")

    # Print full article
    print(f"Article {match['article']} (Page {match['page']}, Position {match['position']})")
    print("=" * 80)
    print(match["content"])


if __name__ == "__main__":
    main()


