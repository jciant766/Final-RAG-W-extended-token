"""
Chapter summarization using Gemini 2.0 Flash via OpenRouter.

Generates concise summaries for each law chapter to enable
fast semantic search across 600+ Maltese laws.
"""

import os
from openai import OpenAI
from typing import Optional
import logging
import time
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ChapterSummarizer:
    """
    Generate chapter summaries using Gemini 2.0 Flash via OpenRouter.

    Summaries are 3-4 sentences covering:
    - What the law regulates
    - Who it applies to
    - Key obligations or rights
    """

    # How much text to use for generating summary
    # First 3500 chars typically captures scope/purpose section
    MAX_CONTEXT_CHARS = 3500

    SYSTEM_PROMPT = """You are a legal document summarizer specializing in Maltese law.
Your task is to create concise, informative summaries of law chapters.

Guidelines:
- Write exactly 3-4 sentences
- Focus on what the law regulates and who it applies to
- Mention key obligations, rights, or penalties if relevant
- Use clear, professional language
- Do not include article numbers or citations in the summary
- Write as if explaining to a legal researcher what this law is about"""

    USER_PROMPT_TEMPLATE = """Summarize this Maltese law chapter in 3-4 sentences.

Chapter Title: {title}

Chapter Text (beginning):
{text}

Summary:"""

    def __init__(self, model: str = "google/gemini-2.0-flash-001"):
        """
        Initialize summarizer with OpenRouter.

        Args:
            model: Model ID on OpenRouter. Default is Gemini 2.0 Flash.
                   Alternatives: "anthropic/claude-3.5-haiku" (slightly more expensive)
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model
        logger.info(f"Initialized ChapterSummarizer with model: {model}")

    def summarize(
        self,
        chapter_title: str,
        chapter_text: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Generate a summary for a law chapter.

        Args:
            chapter_title: Title of the chapter (e.g., "Companies Act")
            chapter_text: Full text of the chapter
            max_retries: Number of retry attempts on failure

        Returns:
            3-4 sentence summary, or None if failed
        """
        # Take first N characters for context
        context_text = chapter_text[:self.MAX_CONTEXT_CHARS]

        prompt = self.USER_PROMPT_TEMPLATE.format(
            title=chapter_title,
            text=context_text
        )

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3  # Slightly creative but focused
                )

                summary = response.choices[0].message.content.strip()

                # Basic validation - summary should be reasonable length
                if len(summary) < 50:
                    logger.warning(f"Summary too short for {chapter_title}, retrying...")
                    continue

                if len(summary) > 1000:
                    # Truncate if too long
                    summary = summary[:1000].rsplit('.', 1)[0] + '.'

                logger.debug(f"Generated summary for {chapter_title}: {len(summary)} chars")
                return summary

            except Exception as e:
                logger.warning(f"Summarization attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue

        logger.error(f"Failed to summarize chapter: {chapter_title}")
        return None

    def summarize_with_fallback(
        self,
        chapter_title: str,
        chapter_text: str
    ) -> str:
        """
        Generate summary with fallback to extractive summary on failure.

        Always returns a summary - uses first sentences if AI fails.
        """
        # Try AI summarization
        summary = self.summarize(chapter_title, chapter_text)

        if summary:
            return summary

        # Fallback: Extract first few sentences
        logger.warning(f"Using extractive fallback for {chapter_title}")
        return self._extractive_fallback(chapter_title, chapter_text)

    def _extractive_fallback(self, chapter_title: str, chapter_text: str) -> str:
        """
        Create a basic summary by extracting key sentences.

        Used when AI summarization fails.
        """
        # Clean up the text
        text = chapter_text[:2000]
        text = ' '.join(text.split())  # Normalize whitespace

        # Try to find sentences that describe purpose
        sentences = []
        for sentence in text.split('.'):
            sentence = sentence.strip()
            if len(sentence) > 20:
                # Look for purpose indicators
                lower = sentence.lower()
                if any(kw in lower for kw in ['to provide', 'to regulate', 'to establish',
                                               'this act', 'this ordinance', 'shall apply']):
                    sentences.append(sentence + '.')
                    if len(sentences) >= 3:
                        break

        if sentences:
            return ' '.join(sentences)

        # Last resort: Just take first 2 substantial sentences
        parts = text.split('.')[:3]
        fallback = '. '.join(p.strip() for p in parts if len(p.strip()) > 20)
        if fallback:
            return fallback + '.'

        return f"{chapter_title} - Maltese legislation."


class BatchSummarizer:
    """
    Batch summarization with rate limiting and progress tracking.

    Use for processing many chapters at once during ingestion.
    """

    def __init__(
        self,
        summarizer: Optional[ChapterSummarizer] = None,
        rate_limit_delay: float = 0.5
    ):
        """
        Args:
            summarizer: ChapterSummarizer instance (creates one if not provided)
            rate_limit_delay: Seconds to wait between API calls
        """
        self.summarizer = summarizer or ChapterSummarizer()
        self.rate_limit_delay = rate_limit_delay

    def summarize_batch(
        self,
        chapters: list,
        progress_callback=None
    ) -> list:
        """
        Summarize multiple chapters with progress tracking.

        Args:
            chapters: List of dicts with 'title' and 'text' keys
            progress_callback: Optional function(current, total) for progress updates

        Returns:
            List of summaries in same order as input
        """
        summaries = []
        total = len(chapters)

        for i, chapter in enumerate(chapters):
            title = chapter.get('title', 'Unknown')
            text = chapter.get('text', '')

            summary = self.summarizer.summarize_with_fallback(title, text)
            summaries.append(summary)

            if progress_callback:
                progress_callback(i + 1, total)

            # Rate limiting
            if i < total - 1:
                time.sleep(self.rate_limit_delay)

        return summaries
