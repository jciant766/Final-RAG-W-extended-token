"""
LLM-as-Judge RAG Evaluation System.

Implements research-backed evaluation methodology (2025-2026):
- QAG (Question-Answer Generation) style claim extraction
- Entity grounding for legal citations (HalluGraph-inspired)
- Chain-of-thought reasoning before scoring
- Normalized 0-1 scores for systematic tracking

Evaluates RAG responses for:
1. Faithfulness - Is the answer supported by retrieved sources?
2. Entity Grounding - Are cited statutes/articles real and accurate?
3. Completeness - Are there missing laws that should have been retrieved?
4. Relevance - Are the retrieved articles actually relevant?

Usage:
    python tests/llm_judge_eval.py --questions 50
    python tests/llm_judge_eval.py --batch  # Use batch API (cheaper, slower)
    python tests/llm_judge_eval.py --question TRAFFIC-001  # Single question

Research basis:
- RAGAS framework (2024-2025)
- HalluGraph for legal RAG (2025)
- LLM-as-Judge best practices (Databricks, Confident AI)
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RetrievalDiagnosis:
    """Diagnosis of retrieval quality against ground truth."""
    expected_laws: List[str]
    found_laws: List[str]
    missed_laws: List[str]
    law_recall: float  # 0-1: what % of expected laws were found

    expected_keywords: List[str]
    found_keywords: List[str]
    missed_keywords: List[str]
    keyword_recall: float  # 0-1: what % of expected keywords were found

    retrieval_success: bool  # Did we get the data we needed?
    failure_reason: str  # "retrieval" or "generation" or "none"


@dataclass
class JudgeVerdict:
    """Result from LLM judge evaluation."""
    question_id: str
    query: str

    # Retrieval Diagnosis: Did we get the right chunks? (Ground Truth comparison)
    retrieval_diagnosis: Optional[RetrievalDiagnosis]

    # Faithfulness: Is answer supported by sources? (QAG-style)
    faithfulness_score: float  # 0.0-1.0 normalized
    faithfulness_reasoning: str
    claims_extracted: List[str]  # All claims found in response
    claims_supported: List[str]  # Claims with source support
    claims_unsupported: List[str]  # Claims without support (hallucinations)

    # Entity Grounding: Are legal citations accurate? (HalluGraph-inspired)
    entity_grounding_score: float  # 0.0-1.0
    entity_grounding_reasoning: str
    citations_found: List[str]  # All citations in response
    citations_verified: List[str]  # Citations that match source docs
    citations_fabricated: List[str]  # Citations not in source docs

    # Completeness: Did we get all relevant laws?
    completeness_score: float  # 0.0-1.0 normalized
    completeness_reasoning: str
    missing_laws_suggested: List[str]
    cross_references_found: List[str]

    # Relevance: Are retrieved articles on-topic?
    relevance_score: float  # 0.0-1.0 normalized
    relevance_reasoning: str
    irrelevant_articles: List[str]

    # Overall
    overall_score: float  # 0.0-1.0 weighted average
    verdict: str  # "accurate", "partial", "inaccurate", "insufficient"

    # Metadata
    judge_model: str
    evaluation_time: float

    # Legacy compatibility (1-5 scale)
    @property
    def faithfulness_score_legacy(self) -> int:
        return max(1, min(5, round(self.faithfulness_score * 4 + 1)))

    @property
    def completeness_score_legacy(self) -> int:
        return max(1, min(5, round(self.completeness_score * 4 + 1)))

    @property
    def relevance_score_legacy(self) -> int:
        return max(1, min(5, round(self.relevance_score * 4 + 1)))


class LLMJudge:
    """
    LLM-as-Judge for RAG evaluation.

    Uses Gemini 2.5 Flash for low hallucination rate.
    """

    # Research-backed prompt with QAG-style claim extraction and entity grounding
    JUDGE_PROMPT = """You are an expert legal RAG evaluator using research-backed methodology.

## Your Task
Evaluate a Maltese Law RAG system's response using a systematic approach.

IMPORTANT: Follow these steps IN ORDER. Think step-by-step before assigning scores.

---
## STEP 1: EXTRACT ALL CLAIMS
First, extract every factual claim from the response. A claim is any statement that can be verified.
Example claims: "The fine is €500", "Article 47 requires...", "Under Cap. 9..."

## STEP 2: VERIFY EACH CLAIM (Faithfulness)
For each claim, check if it is DIRECTLY supported by the retrieved articles.
- SUPPORTED: The exact information appears in the sources
- UNSUPPORTED: The information is not in the sources (hallucination)

Faithfulness Score = (supported claims) / (total claims)
- 1.0: All claims supported
- 0.8+: Minor unsupported details
- 0.5-0.8: Some hallucinations
- <0.5: Major hallucinations

## STEP 3: CHECK ENTITY GROUNDING (Legal Citations)
Extract all legal citations from the response (e.g., "Cap. 9", "Article 47", "S.L. 65.11").
For each citation, verify it exists in the retrieved articles.
- VERIFIED: Citation appears in source documents
- FABRICATED: Citation does not appear (invented statute/article number)

Entity Grounding Score = (verified citations) / (total citations)
This is CRITICAL for legal accuracy. A fabricated "Article 47" is a serious error.

## STEP 4: CHECK COMPLETENESS
Look for cross-references in the retrieved text that weren't followed.
Consider if the topic requires multiple laws.

Completeness Score:
- 1.0: All relevant laws covered
- 0.7+: Minor gaps
- 0.4-0.7: Important laws missing
- <0.4: Critical laws missing

## STEP 5: CHECK RELEVANCE
Are the retrieved articles actually about the question asked?

Relevance Score:
- 1.0: All highly relevant
- 0.7+: Mostly relevant
- 0.4-0.7: Mixed
- <0.4: Mostly irrelevant

---
## INPUT

**Question Asked:**
{question}

**Retrieved Articles:**
{articles}

**RAG System's Response:**
{response}

---
## OUTPUT FORMAT

Respond with this exact JSON structure:
```json
{{
    "step1_claims_extracted": ["<list every factual claim in the response>"],

    "step2_faithfulness": {{
        "claims_supported": ["<claims found in sources>"],
        "claims_unsupported": ["<claims NOT in sources - hallucinations>"],
        "score": <0.0-1.0>,
        "reasoning": "<explain which claims were/weren't supported>"
    }},

    "step3_entity_grounding": {{
        "citations_found": ["<all legal citations in response: Cap.X, Article Y, S.L.Z>"],
        "citations_verified": ["<citations that exist in retrieved articles>"],
        "citations_fabricated": ["<citations NOT in retrieved articles - invented>"],
        "score": <0.0-1.0>,
        "reasoning": "<explain any fabricated citations>"
    }},

    "step4_completeness": {{
        "cross_references_found": ["<cross-refs in retrieved text>"],
        "missing_laws_suggested": ["<laws that should have been retrieved>"],
        "score": <0.0-1.0>,
        "reasoning": "<explain gaps>"
    }},

    "step5_relevance": {{
        "irrelevant_articles": ["<articles not related to question>"],
        "score": <0.0-1.0>,
        "reasoning": "<explain relevance>"
    }},

    "overall_verdict": "<accurate|partial|inaccurate|insufficient>",
    "summary": "<one sentence summary>"
}}
```

IMPORTANT:
- Scores MUST be decimals between 0.0 and 1.0
- Be precise about which claims/citations are unsupported
- Entity grounding is especially important for legal documents
"""

    def __init__(self, model: str = "gemini-2.5-flash"):
        """
        Initialize the LLM Judge.

        Args:
            model: Model to use. Options:
                - "gemini-2.5-flash" (recommended, lowest hallucination)
                - "gemini-2.0-flash"
                - "gpt-4o-mini"
                - "claude-haiku"
        """
        self.model = model
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the appropriate API client."""
        if "gemini" in self.model:
            try:
                import google.generativeai as genai
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found")
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.model.replace("gemini-", "gemini-"))
                self.provider = "google"
                logger.info(f"Initialized Google Gemini: {self.model}")
            except ImportError:
                logger.warning("google-generativeai not installed, falling back to OpenRouter")
                self._init_openrouter()
        elif "gpt" in self.model:
            self._init_openrouter()
        elif "claude" in self.model:
            self._init_openrouter()
        else:
            self._init_openrouter()

    def _init_openrouter(self):
        """Initialize OpenRouter client as fallback."""
        from openai import OpenAI
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.provider = "openrouter"

        # Map model names to OpenRouter format
        model_map = {
            "gemini-2.5-flash": "google/gemini-2.5-flash-preview",
            "gemini-2.0-flash": "google/gemini-2.0-flash-001",
            "gpt-4o-mini": "openai/gpt-4o-mini",
            "claude-haiku": "anthropic/claude-3-5-haiku",
        }
        self.model = model_map.get(self.model, self.model)
        logger.info(f"Initialized OpenRouter: {self.model}")

    def evaluate(
        self,
        question: str,
        response: str,
        articles: List[Dict],
        question_id: str = "unknown"
    ) -> JudgeVerdict:
        """
        Evaluate a single RAG response.

        Args:
            question: The user's question
            response: The RAG system's response
            articles: List of retrieved articles with law_code, article_number, text
            question_id: ID for tracking

        Returns:
            JudgeVerdict with scores and reasoning
        """
        start_time = time.time()

        # Format articles for prompt
        articles_text = self._format_articles(articles)

        # Build prompt
        prompt = self.JUDGE_PROMPT.format(
            question=question,
            articles=articles_text,
            response=response
        )

        # Call LLM
        try:
            if self.provider == "google":
                result = self.client.generate_content(prompt)
                response_text = result.text
            else:
                result = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,  # Zero temperature for reproducibility (research best practice)
                    max_tokens=3000  # Increased for detailed claim extraction
                )
                response_text = result.choices[0].message.content

            # Parse JSON response
            verdict = self._parse_verdict(response_text, question_id, question, time.time() - start_time)
            return verdict

        except Exception as e:
            logger.error(f"Judge evaluation failed: {e}")
            return self._error_verdict(question_id, question, str(e), time.time() - start_time)

    def _format_articles(self, articles: List[Dict]) -> str:
        """Format articles for the prompt.

        NOTE: Previously truncated to 1500 chars, which caused FALSE evaluation failures.
        The generation model sees full text and answers correctly, but the judge couldn't
        verify claims from deeper in articles (e.g., Article 78 is 9756 chars - only 15% was visible).
        Gemini 2.5 Flash has 1M token context, so full articles are fine.
        """
        if not articles:
            return "[No articles retrieved]"

        formatted = []
        for i, art in enumerate(articles, 1):
            law_code = art.get('law_code', 'Unknown')
            art_num = art.get('article_number', '?')
            title = art.get('title', '')
            text = art.get('text', '')  # Full text - no truncation

            formatted.append(f"""
### Article {i}: {law_code} Article {art_num}
**Title:** {title}
**Text:** {text}
""")

        return "\n".join(formatted)

    def _parse_verdict(self, response_text: str, question_id: str, question: str, eval_time: float) -> JudgeVerdict:
        """Parse the JSON verdict from LLM response (research-backed format)."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(json_text.strip())

            # Extract from new step-based structure
            claims = data.get("step1_claims_extracted", [])
            faith = data.get("step2_faithfulness", {})
            entity = data.get("step3_entity_grounding", {})
            comp = data.get("step4_completeness", {})
            rel = data.get("step5_relevance", {})

            # Get scores (already 0-1 normalized)
            f_score = float(faith.get("score", 0.5))
            e_score = float(entity.get("score", 1.0))  # Default to 1.0 if no citations
            c_score = float(comp.get("score", 0.5))
            r_score = float(rel.get("score", 0.5))

            # Clamp scores to 0-1 range
            f_score = max(0.0, min(1.0, f_score))
            e_score = max(0.0, min(1.0, e_score))
            c_score = max(0.0, min(1.0, c_score))
            r_score = max(0.0, min(1.0, r_score))

            # Calculate overall score with entity grounding included
            # Weights: Faithfulness 35%, Entity Grounding 25%, Completeness 20%, Relevance 20%
            overall = (f_score * 0.35 + e_score * 0.25 + c_score * 0.20 + r_score * 0.20)

            return JudgeVerdict(
                question_id=question_id,
                query=question,
                # Retrieval Diagnosis (set later by caller with ground truth)
                retrieval_diagnosis=None,
                # Faithfulness (QAG-style)
                faithfulness_score=f_score,
                faithfulness_reasoning=faith.get("reasoning", ""),
                claims_extracted=claims,
                claims_supported=faith.get("claims_supported", []),
                claims_unsupported=faith.get("claims_unsupported", []),
                # Entity Grounding (HalluGraph-inspired)
                entity_grounding_score=e_score,
                entity_grounding_reasoning=entity.get("reasoning", ""),
                citations_found=entity.get("citations_found", []),
                citations_verified=entity.get("citations_verified", []),
                citations_fabricated=entity.get("citations_fabricated", []),
                # Completeness
                completeness_score=c_score,
                completeness_reasoning=comp.get("reasoning", ""),
                missing_laws_suggested=comp.get("missing_laws_suggested", []),
                cross_references_found=comp.get("cross_references_found", []),
                # Relevance
                relevance_score=r_score,
                relevance_reasoning=rel.get("reasoning", ""),
                irrelevant_articles=rel.get("irrelevant_articles", []),
                # Overall
                overall_score=overall,
                verdict=data.get("overall_verdict", "unknown"),
                judge_model=self.model,
                evaluation_time=eval_time
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse judge response: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return self._error_verdict(question_id, question, f"JSON parse error: {e}", eval_time)
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse verdict fields: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return self._error_verdict(question_id, question, f"Field parse error: {e}", eval_time)

    def _error_verdict(self, question_id: str, question: str, error: str, eval_time: float) -> JudgeVerdict:
        """Return error verdict when evaluation fails."""
        return JudgeVerdict(
            question_id=question_id,
            query=question,
            # Retrieval Diagnosis
            retrieval_diagnosis=None,
            # Faithfulness
            faithfulness_score=0.0,
            faithfulness_reasoning=f"Error: {error}",
            claims_extracted=[],
            claims_supported=[],
            claims_unsupported=[],
            # Entity Grounding
            entity_grounding_score=0.0,
            entity_grounding_reasoning=f"Error: {error}",
            citations_found=[],
            citations_verified=[],
            citations_fabricated=[],
            # Completeness
            completeness_score=0.0,
            completeness_reasoning="",
            missing_laws_suggested=[],
            cross_references_found=[],
            # Relevance
            relevance_score=0.0,
            relevance_reasoning="",
            irrelevant_articles=[],
            # Overall
            overall_score=0.0,
            verdict="error",
            judge_model=self.model,
            evaluation_time=eval_time
        )


class RAGEvaluator:
    """
    Full RAG evaluation pipeline.

    Runs questions through RAG system, then evaluates with LLM judge.
    """

    def __init__(self, judge_model: str = "gemini-2.5-flash"):
        self.judge = LLMJudge(model=judge_model)
        self.retriever = None
        self.generator = None

    def _init_rag(self):
        """Lazy init RAG components."""
        if self.retriever is None:
            from src.retrieval.graphrag_retriever import GraphRAGRetriever
            from src.generation.response_generator import LegalResponseGenerator
            from src.retrieval.enhanced_pipeline import EnhancedRetrievalPipeline

            self.retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
            self.generator = LegalResponseGenerator()
            self.reranker = None
            # Try to init reranker
            try:
                from src.retrieval.reranker import VoyageReranker
                self.reranker = VoyageReranker()
                logger.info("Voyage reranker initialized")
            except Exception as e:
                logger.warning(f"Reranker not available: {e}")

            # Shared enhanced pipeline (same as production)
            self.pipeline = EnhancedRetrievalPipeline(reranker=self.reranker)
            logger.info("RAG components initialized")

    def _rerank_and_filter(
        self,
        query: str,
        articles: List[Dict],
        top_k: int = 5,
        min_relevance: float = 0.2
    ) -> List[Dict]:
        """Delegate to shared enhanced pipeline."""
        return self.pipeline.rerank_and_filter(query, articles, top_k, min_relevance)

    def _boost_definition_articles(
        self,
        articles: List[Dict],
        search_results: Dict
    ) -> List[Dict]:
        """Delegate to shared enhanced pipeline."""
        return self.pipeline.boost_definition_articles(articles, self._fetch_article)

    def _fetch_article(self, law_code: str, article_number: str) -> Optional[Dict]:
        """Fetch a specific article by law code and number."""
        try:
            # Use the retriever's database connection
            if hasattr(self.retriever, 'tables') and 'articles' in self.retriever.tables:
                table = self.retriever.tables['articles']
                filter_str = f"law_code = '{law_code}' AND article_number = '{article_number}'"
                result = table.search().where(filter_str).limit(1).to_pandas()

                if len(result) > 0:
                    if 'vector' in result.columns:
                        result = result.drop(columns=['vector'])
                    record = result.iloc[0].to_dict()
                    return record
        except Exception as e:
            logger.debug(f"Could not fetch article {law_code} Art {article_number}: {e}")
        return None

    def _generate_query_variants(self, query: str) -> List[str]:
        """Delegate to shared enhanced pipeline."""
        return self.pipeline.generate_query_variants(query)

    def _multi_query_search(self, query: str) -> Dict:
        """
        Run multi-query retrieval: search with multiple query variants and merge results.

        Includes a dedicated fundamental law search to ensure large laws (Cap. 9, Cap. 16)
        have sufficient article coverage despite competing with smaller laws.

        Research: Improves recall by catching articles missed by single-query search.
        """
        variants = self._generate_query_variants(query)

        all_articles = []
        all_laws = []
        seen_ids = set()
        seen_law_codes = set()
        classification_info = None
        fundamental_laws_added = []

        for variant in variants:
            results = self.retriever.search(
                query=variant,
                limit=30,  # Wider net for large laws (Cap. 9 has 600+ articles)
                top_laws=15,
                expand_graph=True,
                auto_classify=True
            )

            # Keep classification from first variant (original query)
            if classification_info is None:
                classification_info = results.get('classification')
                fundamental_laws_added = results.get('fundamental_laws_added', [])

            # Collect unique articles
            for art in results.get('articles', []):
                art_id = art.get('id', '')
                if art_id not in seen_ids:
                    seen_ids.add(art_id)
                    all_articles.append(art)

            # Also collect related articles from graph expansion
            for art in results.get('related_articles', []):
                art_id = art.get('id', '')
                if art_id not in seen_ids:
                    seen_ids.add(art_id)
                    all_articles.append(art)

            # Collect unique laws
            for law in results.get('laws', []):
                law_code = law.get('law_code', '')
                if law_code not in seen_law_codes:
                    seen_law_codes.add(law_code)
                    all_laws.append(law)

        # Dedicated fundamental law search: ensure large foundational laws
        # (Cap. 9 Criminal Code, Cap. 16 Civil Code) have enough article coverage.
        # These laws have 600+ articles; the general search across 15 laws may only
        # return 3-5 from them, missing specific crime/topic articles.
        # Use detected categories to determine which fundamental laws need boosting.
        from src.retrieval.graphrag_retriever import FUNDAMENTAL_LAWS
        large_laws = {'Cap. 9', 'Cap. 16', 'Cap. 12'}  # Laws with 300+ articles

        if classification_info and classification_info.get('categories'):
            detected_categories = classification_info['categories']
            for cat in detected_categories:
                for fund_law in FUNDAMENTAL_LAWS.get(cat, []):
                    if fund_law not in large_laws:
                        continue
                    # Count how many articles we already have from this law
                    existing_count = sum(1 for a in all_articles if a.get('law_code') == fund_law)
                    if existing_count < 8:
                        # Do a focused search within just this law
                        focused = self.retriever.search(
                            query=query,
                            limit=15,
                            top_laws=1,
                            expand_graph=False,
                            auto_classify=False,
                            law_filter=fund_law
                        )
                        new_added = 0
                        for art in focused.get('articles', []):
                            art_id = art.get('id', '')
                            if art_id not in seen_ids:
                                seen_ids.add(art_id)
                                all_articles.append(art)
                                new_added += 1
                        if new_added > 0:
                            logger.info(f"Fundamental law boost: {fund_law} had {existing_count} articles, added {new_added} from focused search")

        logger.info(f"Multi-query: {len(all_articles)} unique articles from {len(variants)} queries")

        # Return merged results
        return {
            'articles': all_articles,
            'related_articles': [],  # Already merged above
            'laws': all_laws,
            'query_variants': variants
        }

    def _diagnose_retrieval(
        self,
        articles: List[Dict],
        expected_laws: List[str],
        expected_keywords: List[str],
        verdict_is_bad: bool
    ) -> RetrievalDiagnosis:
        """
        Diagnose retrieval quality against ground truth.

        This answers: "Was the data there but we missed it?"

        Args:
            articles: Retrieved articles
            expected_laws: Laws that SHOULD have been found
            expected_keywords: Keywords that SHOULD appear in retrieved text
            verdict_is_bad: Whether the LLM judge said the answer was bad

        Returns:
            RetrievalDiagnosis with blame attribution
        """
        # Collect all text and law codes from retrieved articles
        all_text = ""
        found_law_codes = set()

        for art in articles:
            law_code = art.get('law_code', '')
            found_law_codes.add(law_code)
            all_text += " " + art.get('text', '')

        all_text_lower = all_text.lower()

        # Check expected laws
        found_laws = []
        missed_laws = []
        for expected in expected_laws:
            # Check if any found law contains the expected code (flexible matching)
            if any(expected.lower() in fl.lower() or fl.lower() in expected.lower()
                   for fl in found_law_codes):
                found_laws.append(expected)
            else:
                missed_laws.append(expected)

        law_recall = len(found_laws) / len(expected_laws) if expected_laws else 1.0

        # Check expected keywords
        found_keywords = []
        missed_keywords = []
        for keyword in expected_keywords:
            if keyword.lower() in all_text_lower:
                found_keywords.append(keyword)
            else:
                missed_keywords.append(keyword)

        keyword_recall = len(found_keywords) / len(expected_keywords) if expected_keywords else 1.0

        # Determine retrieval success (threshold: 50% of both)
        retrieval_success = law_recall >= 0.5 and keyword_recall >= 0.5

        # Blame attribution
        if not retrieval_success:
            failure_reason = "retrieval"  # Data was there but retrieval missed it
        elif verdict_is_bad:
            failure_reason = "generation"  # Got the right data but AI messed up
        else:
            failure_reason = "none"  # Everything worked

        return RetrievalDiagnosis(
            expected_laws=expected_laws,
            found_laws=found_laws,
            missed_laws=missed_laws,
            law_recall=law_recall,
            expected_keywords=expected_keywords,
            found_keywords=found_keywords,
            missed_keywords=missed_keywords,
            keyword_recall=keyword_recall,
            retrieval_success=retrieval_success,
            failure_reason=failure_reason
        )

    def evaluate_questions(
        self,
        questions: List[Dict],
        limit: int = None,
        save_results: bool = True
    ) -> Dict:
        """
        Evaluate a list of test questions with incremental saving.

        Saves progress after each question so no results are lost if
        an API call fails or the process is interrupted mid-run.

        Args:
            questions: List of dicts with 'id', 'query', 'expected_laws', etc.
            limit: Max questions to evaluate
            save_results: Save results to JSON file

        Returns:
            Dict with verdicts and summary statistics
        """
        self._init_rag()

        if limit:
            questions = questions[:limit]

        logger.info(f"Evaluating {len(questions)} questions...")

        verdicts = []
        errors = []

        # Setup incremental save path
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path('tests/eval_results')
        output_dir.mkdir(exist_ok=True)
        incremental_path = output_dir / f"eval_{run_id}_incremental.json"
        final_path = output_dir / f"eval_{run_id}.json"

        def _save_progress(is_final=False):
            """Save current progress to disk."""
            summary = self._calculate_summary(verdicts) if verdicts else {}
            results = {
                'timestamp': datetime.now().isoformat(),
                'run_id': run_id,
                'judge_model': self.judge.model,
                'total_questions': len(questions),
                'completed': len(verdicts) + len(errors),
                'successful_evaluations': len(verdicts),
                'errors': len(errors),
                'is_complete': is_final,
                'summary': summary,
                'verdicts': [asdict(v) for v in verdicts],
                'error_details': errors
            }
            save_path = final_path if is_final else incremental_path
            with open(save_path, 'w') as f:
                json.dump(results, f, indent=2)
            return results

        try:
            for i, q in enumerate(questions):
                logger.info(f"[{i+1}/{len(questions)}] {q.get('id', 'unknown')}: {q.get('query', '')[:50]}...")

                try:
                    # Multi-query retrieval: generate query variants, search with all, merge results
                    search_results = self._multi_query_search(q['query'])

                    # Get merged articles for reranking
                    raw_articles = search_results.get('articles', [])

                    # Multi-query gives us 40-50 candidates. Rerank aggressively to top 5.
                    if len(raw_articles) > 5:
                        articles = self._rerank_and_filter(
                            q['query'], raw_articles,
                            top_k=5,
                            min_relevance=0.25
                        )
                    else:
                        articles = raw_articles[:5]

                    # Boost definition articles - additive only, max 1
                    articles = self._boost_definition_articles(articles, search_results)

                    # Generate response
                    response_data = self.generator.generate(q['query'], articles)
                    response_text = response_data.get('response', '')

                    # Judge the response
                    verdict = self.judge.evaluate(
                        question=q['query'],
                        response=response_text,
                        articles=articles,
                        question_id=q.get('id', f'q_{i}')
                    )

                    # Diagnose retrieval against ground truth (if available)
                    if q.get('expected_laws') or q.get('expected_keywords'):
                        verdict_is_bad = verdict.verdict in ['inaccurate', 'insufficient']
                        diagnosis = self._diagnose_retrieval(
                            articles=articles,
                            expected_laws=q.get('expected_laws', []),
                            expected_keywords=q.get('expected_keywords', []),
                            verdict_is_bad=verdict_is_bad
                        )
                        verdict = JudgeVerdict(
                            question_id=verdict.question_id,
                            query=verdict.query,
                            retrieval_diagnosis=diagnosis,
                            faithfulness_score=verdict.faithfulness_score,
                            faithfulness_reasoning=verdict.faithfulness_reasoning,
                            claims_extracted=verdict.claims_extracted,
                            claims_supported=verdict.claims_supported,
                            claims_unsupported=verdict.claims_unsupported,
                            entity_grounding_score=verdict.entity_grounding_score,
                            entity_grounding_reasoning=verdict.entity_grounding_reasoning,
                            citations_found=verdict.citations_found,
                            citations_verified=verdict.citations_verified,
                            citations_fabricated=verdict.citations_fabricated,
                            completeness_score=verdict.completeness_score,
                            completeness_reasoning=verdict.completeness_reasoning,
                            missing_laws_suggested=verdict.missing_laws_suggested,
                            cross_references_found=verdict.cross_references_found,
                            relevance_score=verdict.relevance_score,
                            relevance_reasoning=verdict.relevance_reasoning,
                            irrelevant_articles=verdict.irrelevant_articles,
                            overall_score=verdict.overall_score,
                            verdict=verdict.verdict,
                            judge_model=verdict.judge_model,
                            evaluation_time=verdict.evaluation_time
                        )

                    verdicts.append(verdict)

                    # Log progress with blame attribution
                    blame = ""
                    if verdict.retrieval_diagnosis:
                        blame = f" | Blame: {verdict.retrieval_diagnosis.failure_reason.upper()}"
                    logger.info(f"  -> Verdict: {verdict.verdict} (F:{verdict.faithfulness_score:.2f} E:{verdict.entity_grounding_score:.2f} C:{verdict.completeness_score:.2f} R:{verdict.relevance_score:.2f}){blame}")

                    # Small delay to avoid rate limits
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"  -> Error: {e}")
                    errors.append({'question_id': q.get('id'), 'error': str(e)})

                # Save progress after every question (success or error)
                if save_results:
                    _save_progress(is_final=False)

        except KeyboardInterrupt:
            logger.warning(f"\nInterrupted! Saving {len(verdicts)} completed results...")
        finally:
            # Always save final results
            if save_results and (verdicts or errors):
                results = _save_progress(is_final=True)
                # Clean up incremental file
                if incremental_path.exists():
                    incremental_path.unlink()
                logger.info(f"Results saved to {final_path} ({len(verdicts)} verdicts, {len(errors)} errors)")

        # Calculate final summary
        summary = self._calculate_summary(verdicts)

        results = {
            'timestamp': datetime.now().isoformat(),
            'run_id': run_id,
            'judge_model': self.judge.model,
            'total_questions': len(questions),
            'completed': len(verdicts) + len(errors),
            'successful_evaluations': len(verdicts),
            'errors': len(errors),
            'is_complete': True,
            'summary': summary,
            'verdicts': [asdict(v) for v in verdicts],
            'error_details': errors
        }

        return results

    def _calculate_summary(self, verdicts: List[JudgeVerdict]) -> Dict:
        """Calculate summary statistics from verdicts (research-backed metrics)."""
        if not verdicts:
            return {}

        # Filter out errors
        valid = [v for v in verdicts if v.verdict != "error"]

        if not valid:
            return {'error': 'No valid evaluations'}

        # Score averages (0-1 scale)
        avg_faith = sum(v.faithfulness_score for v in valid) / len(valid)
        avg_entity = sum(v.entity_grounding_score for v in valid) / len(valid)
        avg_comp = sum(v.completeness_score for v in valid) / len(valid)
        avg_rel = sum(v.relevance_score for v in valid) / len(valid)
        avg_overall = sum(v.overall_score for v in valid) / len(valid)

        # Verdict distribution
        verdict_counts = {}
        for v in valid:
            verdict_counts[v.verdict] = verdict_counts.get(v.verdict, 0) + 1

        # Collect issues for analysis
        all_unsupported_claims = []
        all_fabricated_citations = []
        all_missing_laws = []

        for v in valid:
            all_unsupported_claims.extend(v.claims_unsupported)
            all_fabricated_citations.extend(v.citations_fabricated)
            all_missing_laws.extend(v.missing_laws_suggested)

        # Count claims for QAG-style metrics
        total_claims = sum(len(v.claims_extracted) for v in valid)
        supported_claims = sum(len(v.claims_supported) for v in valid)
        total_citations = sum(len(v.citations_found) for v in valid)
        verified_citations = sum(len(v.citations_verified) for v in valid)

        # Blame attribution from retrieval diagnosis
        with_diagnosis = [v for v in valid if v.retrieval_diagnosis is not None]
        blame_counts = {'retrieval': 0, 'generation': 0, 'none': 0}
        retrieval_recall_sum = 0
        keyword_recall_sum = 0

        for v in with_diagnosis:
            blame_counts[v.retrieval_diagnosis.failure_reason] += 1
            retrieval_recall_sum += v.retrieval_diagnosis.law_recall
            keyword_recall_sum += v.retrieval_diagnosis.keyword_recall

        avg_law_recall = retrieval_recall_sum / len(with_diagnosis) if with_diagnosis else None
        avg_keyword_recall = keyword_recall_sum / len(with_diagnosis) if with_diagnosis else None

        return {
            'scores': {
                'faithfulness': round(avg_faith, 3),
                'entity_grounding': round(avg_entity, 3),
                'completeness': round(avg_comp, 3),
                'relevance': round(avg_rel, 3),
                'overall': round(avg_overall, 3)
            },
            'qag_metrics': {
                'total_claims_extracted': total_claims,
                'claims_supported': supported_claims,
                'claims_support_rate': round(supported_claims / total_claims, 3) if total_claims > 0 else 1.0,
                'total_citations': total_citations,
                'citations_verified': verified_citations,
                'citation_accuracy_rate': round(verified_citations / total_citations, 3) if total_citations > 0 else 1.0
            },
            'blame_attribution': {
                'retrieval_failures': blame_counts['retrieval'],
                'generation_failures': blame_counts['generation'],
                'successes': blame_counts['none'],
                'avg_law_recall': round(avg_law_recall, 3) if avg_law_recall else None,
                'avg_keyword_recall': round(avg_keyword_recall, 3) if avg_keyword_recall else None,
                'questions_with_ground_truth': len(with_diagnosis)
            },
            'verdict_distribution': verdict_counts,
            'accuracy_rate': round(verdict_counts.get('accurate', 0) / len(valid) * 100, 1),
            'common_unsupported_claims': list(set(all_unsupported_claims))[:10],
            'fabricated_citations': list(set(all_fabricated_citations))[:10],
            'commonly_missing_laws': list(set(all_missing_laws))[:10],
            'total_evaluated': len(valid)
        }


def run_evaluation(
    num_questions: int = 50,
    judge_model: str = "gemini-2.5-flash",
    question_id: str = None
):
    """Run the evaluation pipeline."""
    from comprehensive_rag_eval import TEST_QUESTIONS

    # Convert dataclass questions to dicts
    questions = [
        {
            'id': q.id,
            'query': q.query,
            'category': q.category,
            'expected_laws': q.expected_laws,
            'expected_keywords': q.expected_keywords,
            'notes': q.notes
        }
        for q in TEST_QUESTIONS
    ]

    # Filter to single question if specified
    if question_id:
        questions = [q for q in questions if q['id'] == question_id]
        if not questions:
            print(f"Question {question_id} not found")
            return

    evaluator = RAGEvaluator(judge_model=judge_model)
    results = evaluator.evaluate_questions(questions, limit=num_questions)

    # Print summary (clean, readable format)
    summary = results.get('summary', {})
    scores = summary.get('scores', {})
    qag = summary.get('qag_metrics', {})
    blame = summary.get('blame_attribution', {})

    print("\n")
    print("+" + "-" * 68 + "+")
    print("|" + " RAG EVALUATION RESULTS ".center(68) + "|")
    print("+" + "-" * 68 + "+")

    # Meta info
    print(f"|  Judge Model:        {results.get('judge_model', 'N/A'):<44} |")
    print(f"|  Questions Evaluated: {summary.get('total_evaluated', 0):<43} |")
    print("+" + "-" * 68 + "+")

    # Main Scores
    print("|" + " QUALITY SCORES (0-1 scale) ".center(68) + "|")
    print("+" + "-" * 68 + "+")

    def score_bar(score, width=20):
        """Create a visual bar for score (ASCII-safe for Windows)."""
        if not isinstance(score, (int, float)):
            return "N/A".ljust(width)
        filled = int(score * width)
        bar = "#" * filled + "-" * (width - filled)
        return f"[{bar}] {score:.1%}"

    faith = scores.get('faithfulness', 0)
    entity = scores.get('entity_grounding', 0)
    comp = scores.get('completeness', 0)
    rel = scores.get('relevance', 0)
    overall = scores.get('overall', 0)

    print(f"|  Faithfulness:      {score_bar(faith):<45} |")
    print(f"|  Entity Grounding:  {score_bar(entity):<45} |")
    print(f"|  Completeness:      {score_bar(comp):<45} |")
    print(f"|  Relevance:         {score_bar(rel):<45} |")
    print("|" + "-" * 68 + "|")
    print(f"|  OVERALL:           {score_bar(overall):<45} |")
    print("+" + "-" * 68 + "+")

    # Claim Analysis
    print("|" + " CLAIM ANALYSIS ".center(68) + "|")
    print("+" + "-" * 68 + "+")
    total_claims = qag.get('total_claims_extracted', 0)
    supported = qag.get('claims_supported', 0)
    claim_rate = qag.get('claims_support_rate', 0)
    total_cites = qag.get('total_citations', 0)
    verified = qag.get('citations_verified', 0)
    cite_rate = qag.get('citation_accuracy_rate', 0)

    print(f"|  Claims:    {supported:>4} / {total_claims:<4} supported ({claim_rate:.0%})".ljust(68) + " |")
    print(f"|  Citations: {verified:>4} / {total_cites:<4} verified  ({cite_rate:.0%})".ljust(68) + " |")
    print("+" + "-" * 68 + "+")

    # Blame Attribution
    if blame.get('questions_with_ground_truth', 0) > 0:
        print("|" + " WHERE DID FAILURES HAPPEN? ".center(68) + "|")
        print("+" + "-" * 68 + "+")

        ret_fail = blame.get('retrieval_failures', 0)
        gen_fail = blame.get('generation_failures', 0)
        success = blame.get('successes', 0)
        total = ret_fail + gen_fail + success

        if total > 0:
            print(f"|  Retrieval failed:   {ret_fail:>3}  ({ret_fail/total*100:>5.1f}%)  <- Data existed, search missed it".ljust(68) + " |")
            print(f"|  Generation failed:  {gen_fail:>3}  ({gen_fail/total*100:>5.1f}%)  <- Found data, AI made errors".ljust(68) + " |")
            print(f"|  Success:            {success:>3}  ({success/total*100:>5.1f}%)".ljust(68) + " |")

        if blame.get('avg_law_recall') is not None:
            print("|" + "-" * 68 + "|")
            print(f"|  Avg Law Recall:     {blame.get('avg_law_recall'):.0%}".ljust(68) + " |")
            print(f"|  Avg Keyword Recall: {blame.get('avg_keyword_recall'):.0%}".ljust(68) + " |")

        print("+" + "-" * 68 + "+")

    # Verdict Distribution
    print("|" + " VERDICT BREAKDOWN ".center(68) + "|")
    print("+" + "-" * 68 + "+")
    for verdict, count in sorted(summary.get('verdict_distribution', {}).items()):
        pct = count / summary.get('total_evaluated', 1) * 100
        bar_len = int(pct / 5)
        bar = "*" * bar_len
        print(f"|  {verdict:<12} {count:>3}  {bar:<20} ({pct:.0f}%)".ljust(68) + " |")
    print("+" + "-" * 68 + "+")

    # Issues Found
    has_issues = (summary.get('common_unsupported_claims') or
                  summary.get('fabricated_citations') or
                  summary.get('commonly_missing_laws'))

    if has_issues:
        print("|" + " ISSUES DETECTED ".center(68) + "|")
        print("+" + "-" * 68 + "+")

        if summary.get('fabricated_citations'):
            print("|  FABRICATED CITATIONS (Critical):".ljust(68) + " |")
            for c in summary['fabricated_citations'][:3]:
                print(f"|    - {c[:58]}".ljust(68) + " |")

        if summary.get('common_unsupported_claims'):
            print("|  UNSUPPORTED CLAIMS:".ljust(68) + " |")
            for h in summary['common_unsupported_claims'][:3]:
                print(f"|    - {h[:58]}".ljust(68) + " |")

        if summary.get('commonly_missing_laws'):
            print("|  MISSING LAWS:".ljust(68) + " |")
            for law in summary['commonly_missing_laws'][:3]:
                print(f"|    - {law[:58]}".ljust(68) + " |")

        print("+" + "-" * 68 + "+")

    # Final verdict
    accuracy = summary.get('accuracy_rate', 0)
    if accuracy >= 80:
        status = "GOOD"
    elif accuracy >= 60:
        status = "NEEDS WORK"
    else:
        status = "POOR"

    print("|" + f" ACCURACY: {accuracy:.1f}% - {status} ".center(68) + "|")
    print("+" + "-" * 68 + "+")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM-as-Judge RAG Evaluation")
    parser.add_argument("--questions", "-n", type=int, default=50, help="Number of questions to evaluate")
    parser.add_argument("--model", "-m", type=str, default="gemini-2.5-flash",
                       choices=["gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o-mini", "claude-haiku"],
                       help="Judge model to use")
    parser.add_argument("--question", "-q", type=str, help="Evaluate single question by ID")

    args = parser.parse_args()

    run_evaluation(
        num_questions=args.questions,
        judge_model=args.model,
        question_id=args.question
    )
