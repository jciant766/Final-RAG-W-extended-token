import os
import json
import argparse
from typing import List, Dict, Any

import openai
from dotenv import load_dotenv


def load_api_key() -> None:
    """Load OpenAI API key from environment or optional 'env' file, mirroring existing setup."""
    load_dotenv()
    if os.path.exists('env'):
        load_dotenv('env', override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import streamlit as st  # type: ignore
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            pass

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    openai.api_key = api_key


def extract_articles_from_text(full_text: str) -> List[Dict[str, Any]]:
    """Reuse the tokenizer-aware article extraction from doc_processor.
    Returns a list of dicts: { 'article': str, 'content': str, 'page': int, 'position': int }
    """
    # Import here to avoid a hard dependency if this module is used elsewhere
    from doc_processor import DocumentProcessor  # local module

    processor = DocumentProcessor()
    # Reuse internal extraction to get consistent article IDs and basic metadata
    articles = processor._extract_articles(full_text)  # noqa: SLF001 - intentional reuse
    return articles


def build_prompt(article_id: str, article_text: str) -> str:
    """Create a strict instruction to produce only JSON with the requested schema."""
    template = """
You are extracting structured data from statutory text of the Malta Commercial Code.
ONLY use the content provided below. Do not invent facts. If an item is not present, return null or an empty array as appropriate.

TARGET ARTICLE: {article_id}

ARTICLE TEXT:
{article_text}

OUTPUT STRICTLY AS COMPACT JSON (no prose), matching this schema:
{{
  "article_number": "string",
  "title": "string|null",
  "definitions": [{{"term": "string", "definition": "string", "citation": "string"}}],
  "requirements": [{{"subject": "string", "obligation": "string", "citation": "string"}}],
  "penalties": [{{"violation": "string", "penalty": "string", "citation": "string"}}]
}}

Rules:
- For citation use the format: "Article {article_id}".
- "title" should be the article's short heading if clearly present; otherwise null.
- Definitions are terms defined (look for phrases like "means", "includes").
- Requirements/obligations use modalities like "shall", "must", "is required to".
- Penalties/sanctions include fines, imprisonment, or other sanctions.
- Return valid JSON only, no markdown.
"""
    return template.format(article_id=article_id, article_text=article_text)


def extract_one_article(article: Dict[str, Any], model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 500) -> Dict[str, Any]:
    """Call OpenAI to extract structured data for a single article."""
    article_id = str(article.get('article', ''))
    content = article.get('content', '')
    prompt = build_prompt(article_id, content)

    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise legal information extractor. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    text = response.choices[0].message.content.strip()

    try:
        data = json.loads(text)
    except Exception:
        # Attempt a minimal cleanup if model wrapped JSON in code fences
        cleaned = text
        if cleaned.startswith("```"):
            cleaned = cleaned.strip('`')
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        data = json.loads(cleaned)

    # Ensure article_number is set if model omitted or mismatched
    if not isinstance(data, dict):
        raise ValueError("Model did not return a JSON object")
    data.setdefault("article_number", article_id)

    # Normalize arrays and fields
    for key in ["definitions", "requirements", "penalties"]:
        if key not in data or not isinstance(data[key], list):
            data[key] = []

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured statutory data from Malta Commercial Code articles.")
    parser.add_argument("--path", default="malta_commercial_code_text.txt", help="Path to statutory text file")
    parser.add_argument("--limit", type=int, default=3, help="Number of articles to process (for testing)")
    parser.add_argument("--articles", type=str, default="", help="Comma-separated article IDs to include (e.g., 1,2,26A). Overrides --limit if provided.")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI chat model to use")
    parser.add_argument("--out", default="extracted_statutory_data.json", help="Output JSON file")
    args = parser.parse_args()

    load_api_key()

    if not os.path.exists(args.path):
        raise FileNotFoundError(f"Statutory text not found at {args.path}")

    with open(args.path, "r", encoding="utf-8") as f:
        full_text = f.read()

    articles = extract_articles_from_text(full_text)

    # Filter selection
    selected: List[Dict[str, Any]]
    if args.articles:
        wanted = {a.strip().upper() for a in args.articles.split(',') if a.strip()}
        selected = [a for a in articles if str(a.get('article', '')).upper() in wanted]
    else:
        selected = articles[: max(0, args.limit)]

    results: List[Dict[str, Any]] = []
    for idx, art in enumerate(selected, start=1):
        try:
            data = extract_one_article(art, model=args.model, temperature=0.2, max_tokens=500)
            results.append(data)
            print(f"Processed {idx}/{len(selected)}: Article {art.get('article')}")
        except Exception as e:
            print(f"Error processing Article {art.get('article')}: {e}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(results)} records to {args.out}")


if __name__ == "__main__":
    main()


