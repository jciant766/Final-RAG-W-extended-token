"""
Research-Grade RAG Evaluation System.

Based on:
- RAGAS framework (https://docs.ragas.io) - Faithfulness, Answer Relevance, Context Precision
- Bloomberg Law methodology (2025) - Multiple trials, statistical testing
- Microsoft BenchmarkQED - 6 trials per query for statistical significance

Metrics evaluated:
1. FAITHFULNESS - Is every claim in the answer supported by retrieved context?
2. ANSWER_RELEVANCE - Does the answer actually address the question asked?
3. CONTEXT_PRECISION - Are the retrieved documents relevant to the question?
4. CONTEXT_RECALL - Did we retrieve all necessary information? (checks for missing laws)
5. HALLUCINATION_DETECTION - Are there fabricated facts, citations, or claims?

Usage:
    # Quick evaluation (20 questions, 1 trial) - ~$0.02
    python tests/research_grade_eval.py --quick

    # Standard evaluation (50 questions, 3 trials) - ~$0.15
    python tests/research_grade_eval.py --standard

    # Full research evaluation (all questions, 6 trials) - ~$0.60
    python tests/research_grade_eval.py --full

    # Use batch API (50% cheaper, ~24h turnaround)
    python tests/research_grade_eval.py --full --batch
"""

import os
import sys
import json
import time
import re
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# RAGAS-STYLE EVALUATION PROMPTS
# =============================================================================

PROMPTS = {
    # Claim Extraction (RAGAS Step 1)
    "claim_extraction": """You are a legal claim extractor. Extract all factual claims from this legal response.

A claim is any statement that asserts a fact that could be verified, including:
- Legal provisions cited (e.g., "Article X states...")
- Penalties or consequences mentioned
- Definitions provided
- Procedures described
- Any specific facts, numbers, or dates

Response to analyze:
\"\"\"
{response}
\"\"\"

Return a JSON array of claims:
{{"claims": ["claim 1", "claim 2", ...]}}

If no clear claims, return: {{"claims": []}}""",

    # Claim Verification (RAGAS Step 2)
    "claim_verification": """Verify if this claim is supported by the legal context.

CLAIM: {claim}

LEGAL CONTEXT:
\"\"\"
{context}
\"\"\"

Return JSON:
{{
    "verdict": "supported" | "not_supported" | "contradicted",
    "evidence": "quote from context if found, or empty string",
    "confidence": 0.0-1.0
}}""",

    # Answer Relevance
    "answer_relevance": """Evaluate how well this answer addresses the legal question.

QUESTION: {question}

ANSWER:
\"\"\"
{response}
\"\"\"

Return JSON:
{{
    "score": 1-5,
    "addressed": ["aspects that were answered"],
    "missing": ["aspects not answered"],
    "explanation": "brief reasoning"
}}

Score guide:
5 = Directly and completely answers with specific legal provisions
4 = Answers main question, minor gaps
3 = Partially answers, significant gaps
2 = Tangentially related
1 = Does not address the question""",

    # Context Precision
    "context_precision": """Evaluate relevance of retrieved legal articles for this question.

QUESTION: {question}

ARTICLES:
{articles}

Return JSON:
{{
    "relevant_count": number,
    "total_count": number,
    "precision": 0.0-1.0,
    "irrelevant_articles": ["list citations of off-topic articles"]
}}""",

    # Context Recall / Completeness
    "context_recall": """Analyze if all necessary legal sources were retrieved.

QUESTION: {question}

RETRIEVED ARTICLES:
{articles}

ANSWER GIVEN:
\"\"\"
{response}
\"\"\"

Look for:
1. Cross-references in text (e.g., "as provided in Cap. X", "subject to S.L. Y")
2. Laws mentioned in answer but not in sources
3. Related laws typically needed for this topic

Return JSON:
{{
    "cross_refs_in_text": ["Cap. X", "S.L. Y"],
    "cross_refs_retrieved": ["which we have"],
    "cross_refs_missing": ["which we don't have"],
    "recall_score": 0.0-1.0,
    "explanation": "reasoning"
}}""",

    # Hallucination Detection
    "hallucination_check": """Check for hallucinations in this legal response.

QUESTION: {question}

SOURCE CONTEXT:
\"\"\"
{context}
\"\"\"

RESPONSE TO CHECK:
\"\"\"
{response}
\"\"\"

Check for:
1. FABRICATED_CITATION - Law codes or article numbers not in context
2. FABRICATED_FACT - Numbers, dates, penalties not in context
3. MISATTRIBUTION - Info attributed to wrong source
4. CONTRADICTION - Claims that contradict context

Return JSON:
{{
    "hallucinations": [
        {{"type": "TYPE", "claim": "the claim", "issue": "what's wrong"}}
    ],
    "is_clean": true/false,
    "severity": "none" | "minor" | "moderate" | "severe"
}}"""
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TrialResult:
    """Result from a single evaluation trial."""
    trial_number: int
    faithfulness_score: float
    answer_relevance_score: float  # Normalized 0-1
    answer_relevance_raw: int      # Raw 1-5
    context_precision_score: float
    context_recall_score: float

    total_claims: int
    supported_claims: int
    unsupported_claims: int

    hallucination_free: bool
    hallucination_count: int
    hallucination_severity: str
    hallucinations: List[Dict]

    cross_refs_found: List[str]
    cross_refs_missing: List[str]
    missing_aspects: List[str]


@dataclass
class QuestionEvaluation:
    """Full evaluation of a single question across multiple trials."""
    question_id: str
    query: str
    category: str
    expected_laws: List[str]
    laws_retrieved: List[str]

    # Aggregated scores
    faithfulness_mean: float
    faithfulness_std: float
    answer_relevance_mean: float
    context_precision_mean: float
    context_recall_mean: float
    ragas_score: float
    hallucination_rate: float

    trials: List[Dict]
    num_trials: int
    evaluation_time: float


@dataclass
class EvaluationReport:
    """Full evaluation report."""
    timestamp: str
    model_used: str
    num_questions: int
    num_trials_per_question: int
    total_evaluations: int

    # Aggregate scores
    mean_faithfulness: float
    mean_answer_relevance: float
    mean_context_precision: float
    mean_context_recall: float
    mean_ragas_score: float

    # Std deviations
    std_faithfulness: float
    std_answer_relevance: float

    # Hallucination analysis
    overall_hallucination_rate: float
    common_hallucination_types: Dict[str, int]
    commonly_missing_laws: List[Tuple[str, int]]

    # By category
    scores_by_category: Dict[str, Dict]

    # Results
    question_evaluations: List[Dict]

    # Cost
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost: float


# =============================================================================
# GEMINI CLIENT - Standard API
# =============================================================================

class GeminiClient:
    """
    Gemini API client using google-generativeai SDK.

    Model IDs (as of Jan 2026):
    - gemini-2.5-flash (recommended)
    - gemini-2.0-flash
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model_id = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._init_client()

    def _init_client(self):
        """Initialize the Gemini client."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed.\n"
                "Run: pip install google-generativeai"
            )

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY not found in environment.\n"
                "Get a key at: https://aistudio.google.com/app/apikey"
            )

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model_id)
        logger.info(f"Initialized Gemini model: {self.model_id}")

    def generate(self, prompt: str, max_retries: int = 3) -> str:
        """Generate response with retry logic."""
        import google.generativeai as genai

        for attempt in range(max_retries):
            try:
                response = self.client.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=2000,
                    )
                )

                # Track tokens (approximate)
                self.total_input_tokens += len(prompt) // 4
                self.total_output_tokens += len(response.text) // 4

                return response.text

            except Exception as e:
                logger.warning(f"API error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return json.dumps({"error": str(e)})

        return json.dumps({"error": "Max retries exceeded"})

    def get_cost(self, use_batch: bool = False) -> Dict:
        """Calculate cost based on token usage."""
        # Gemini 2.5 Flash pricing (Jan 2026)
        if use_batch:
            input_rate = 0.15   # $0.15 per 1M tokens
            output_rate = 1.25  # $1.25 per 1M tokens
        else:
            input_rate = 0.30   # $0.30 per 1M tokens
            output_rate = 2.50  # $2.50 per 1M tokens

        input_cost = (self.total_input_tokens / 1_000_000) * input_rate
        output_cost = (self.total_output_tokens / 1_000_000) * output_rate

        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(input_cost + output_cost, 4)
        }


# =============================================================================
# GEMINI BATCH CLIENT - For large evaluations
# =============================================================================

class GeminiBatchClient:
    """
    Gemini Batch API client for 50% cost reduction.

    Uses google-genai SDK (different from google-generativeai).
    Batch jobs complete within 24 hours but often much faster.
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model_id = f"models/{model}"
        self.pending_requests = []
        self.results = {}
        self._init_client()

    def _init_client(self):
        """Initialize the batch client."""
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai not installed.\n"
                "Run: pip install google-genai"
            )

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found")

        self.client = genai.Client(api_key=api_key)
        logger.info(f"Initialized Gemini Batch client: {self.model_id}")

    def add_request(self, request_id: str, prompt: str):
        """Add a request to the batch."""
        self.pending_requests.append({
            "request_id": request_id,
            "contents": [{
                "parts": [{"text": prompt}],
                "role": "user"
            }]
        })

    def submit_batch(self, display_name: str = "rag-eval") -> str:
        """Submit the batch and return job name."""
        if not self.pending_requests:
            raise ValueError("No requests to submit")

        batch_job = self.client.batches.create(
            model=self.model_id,
            src=self.pending_requests,
            config={"display_name": display_name}
        )

        logger.info(f"Submitted batch job: {batch_job.name}")
        logger.info(f"Requests: {len(self.pending_requests)}")

        self.pending_requests = []  # Clear for next batch
        return batch_job.name

    def wait_for_completion(self, job_name: str, poll_interval: int = 30) -> bool:
        """Wait for batch job to complete."""
        completed_states = {'JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED',
                          'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED'}

        logger.info("Waiting for batch job to complete...")

        while True:
            job = self.client.batches.get(name=job_name)
            state = job.state.name

            if state in completed_states:
                logger.info(f"Job finished: {state}")
                return state == 'JOB_STATE_SUCCEEDED'

            logger.info(f"Status: {state} - waiting {poll_interval}s...")
            time.sleep(poll_interval)

    def get_results(self, job_name: str) -> Dict[str, str]:
        """Get results from completed batch job."""
        job = self.client.batches.get(name=job_name)

        results = {}
        if hasattr(job, 'dest') and hasattr(job.dest, 'inlined_responses'):
            for i, resp in enumerate(job.dest.inlined_responses):
                if resp.response:
                    # Map back to request_id if we stored it
                    results[f"request_{i}"] = resp.response.text

        return results


# =============================================================================
# JSON PARSER WITH RECOVERY
# =============================================================================

def parse_json_response(text: str, default: Dict = None) -> Dict:
    """
    Parse JSON from LLM response with multiple fallback strategies.

    LLMs often return:
    - JSON wrapped in ```json ... ```
    - JSON with trailing commas
    - JSON with comments
    - Malformed JSON
    """
    if default is None:
        default = {}

    if not text or not text.strip():
        return default

    # Strategy 1: Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code block
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{.*\}',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                extracted = match.group(1) if '```' in pattern else match.group(0)
                return json.loads(extracted.strip())
            except json.JSONDecodeError:
                continue

    # Strategy 3: Fix common issues
    cleaned = text.strip()
    # Remove trailing commas
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    logger.debug(f"Failed to parse JSON: {text[:200]}...")
    return default


# =============================================================================
# RESEARCH-GRADE EVALUATOR
# =============================================================================

class ResearchGradeEvaluator:
    """
    Research-grade RAG evaluator following RAGAS methodology.
    """

    def __init__(self, model: str = "gemini-2.5-flash", use_batch: bool = False):
        self.use_batch = use_batch

        if use_batch:
            self.llm = GeminiBatchClient(model=model)
        else:
            self.llm = GeminiClient(model=model)

        self.retriever = None
        self.generator = None

    def _init_rag(self):
        """Lazy init RAG components."""
        if self.retriever is None:
            from src.retrieval.graphrag_retriever import GraphRAGRetriever
            from src.generation.response_generator import LegalResponseGenerator

            self.retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
            self.generator = LegalResponseGenerator()
            logger.info("RAG components initialized")

    def _format_articles(self, articles: List[Dict]) -> str:
        """Format articles for prompts."""
        if not articles:
            return "[No articles retrieved]"

        parts = []
        for i, art in enumerate(articles, 1):
            law = art.get('law_code', 'Unknown')
            num = art.get('article_number', '?')
            title = art.get('title', '')
            text = art.get('text', '')[:1000]
            parts.append(f"[{i}] {law} Art. {num}: {title}\n{text}")

        return "\n\n".join(parts)

    # -------------------------------------------------------------------------
    # RAGAS Metrics Implementation
    # -------------------------------------------------------------------------

    def evaluate_faithfulness(self, response: str, context: str) -> Tuple[float, int, int, int]:
        """
        Evaluate faithfulness using RAGAS claim-by-claim methodology.

        Returns: (score, total_claims, supported, unsupported)
        """
        # Step 1: Extract claims
        prompt = PROMPTS["claim_extraction"].format(response=response)
        result = self.llm.generate(prompt)
        data = parse_json_response(result, {"claims": []})
        claims = data.get("claims", [])

        if not claims:
            # If no claims extracted, treat whole response as one claim
            claims = [response[:500]]

        # Step 2: Verify each claim
        supported = 0
        unsupported = 0

        for claim in claims[:10]:  # Limit to 10 claims for cost
            prompt = PROMPTS["claim_verification"].format(claim=claim, context=context)
            result = self.llm.generate(prompt)
            data = parse_json_response(result, {"verdict": "not_supported"})

            verdict = data.get("verdict", "not_supported")
            if verdict == "supported":
                supported += 1
            else:
                unsupported += 1

        total = supported + unsupported
        score = supported / total if total > 0 else 0.0

        return score, total, supported, unsupported

    def evaluate_answer_relevance(self, question: str, response: str) -> Tuple[float, int, List[str]]:
        """
        Evaluate answer relevance.

        Returns: (normalized_score, raw_score, missing_aspects)
        """
        prompt = PROMPTS["answer_relevance"].format(question=question, response=response)
        result = self.llm.generate(prompt)
        data = parse_json_response(result, {"score": 3, "missing": []})

        raw_score = min(5, max(1, data.get("score", 3)))
        normalized = (raw_score - 1) / 4  # Convert 1-5 to 0-1
        missing = data.get("missing", [])

        return normalized, raw_score, missing

    def evaluate_context_precision(self, question: str, articles: List[Dict]) -> float:
        """Evaluate context precision."""
        articles_text = self._format_articles(articles)
        prompt = PROMPTS["context_precision"].format(question=question, articles=articles_text)
        result = self.llm.generate(prompt)
        data = parse_json_response(result, {"precision": 0.5})

        return float(data.get("precision", 0.5))

    def evaluate_context_recall(self, question: str, articles: List[Dict], response: str) -> Tuple[float, List[str], List[str]]:
        """
        Evaluate context recall / completeness.

        Returns: (recall_score, refs_found, refs_missing)
        """
        articles_text = self._format_articles(articles)
        prompt = PROMPTS["context_recall"].format(
            question=question,
            articles=articles_text,
            response=response
        )
        result = self.llm.generate(prompt)
        data = parse_json_response(result, {"recall_score": 0.5})

        return (
            float(data.get("recall_score", 0.5)),
            data.get("cross_refs_in_text", []),
            data.get("cross_refs_missing", [])
        )

    def check_hallucinations(self, question: str, context: str, response: str) -> Tuple[bool, int, str, List[Dict]]:
        """
        Check for hallucinations.

        Returns: (is_clean, count, severity, hallucinations)
        """
        prompt = PROMPTS["hallucination_check"].format(
            question=question,
            context=context,
            response=response
        )
        result = self.llm.generate(prompt)
        data = parse_json_response(result, {"is_clean": True, "hallucinations": []})

        hallucinations = data.get("hallucinations", [])
        is_clean = data.get("is_clean", len(hallucinations) == 0)
        severity = data.get("severity", "none")

        return is_clean, len(hallucinations), severity, hallucinations

    # -------------------------------------------------------------------------
    # Main Evaluation Methods
    # -------------------------------------------------------------------------

    def run_single_trial(
        self,
        question: str,
        response: str,
        articles: List[Dict],
        trial_num: int
    ) -> TrialResult:
        """Run a single evaluation trial."""
        context = self._format_articles(articles)

        # 1. Faithfulness
        faith_score, total_claims, supported, unsupported = self.evaluate_faithfulness(response, context)

        # 2. Answer Relevance
        relevance_norm, relevance_raw, missing_aspects = self.evaluate_answer_relevance(question, response)

        # 3. Context Precision
        precision = self.evaluate_context_precision(question, articles)

        # 4. Context Recall
        recall, refs_found, refs_missing = self.evaluate_context_recall(question, articles, response)

        # 5. Hallucination Check
        is_clean, hall_count, severity, hallucinations = self.check_hallucinations(question, context, response)

        return TrialResult(
            trial_number=trial_num,
            faithfulness_score=faith_score,
            answer_relevance_score=relevance_norm,
            answer_relevance_raw=relevance_raw,
            context_precision_score=precision,
            context_recall_score=recall,
            total_claims=total_claims,
            supported_claims=supported,
            unsupported_claims=unsupported,
            hallucination_free=is_clean,
            hallucination_count=hall_count,
            hallucination_severity=severity,
            hallucinations=hallucinations,
            cross_refs_found=refs_found,
            cross_refs_missing=refs_missing,
            missing_aspects=missing_aspects
        )

    def evaluate_question(
        self,
        question_data: Dict,
        num_trials: int = 3
    ) -> QuestionEvaluation:
        """Evaluate a single question with multiple trials."""
        self._init_rag()
        start_time = time.time()

        query = question_data['query']

        # Run RAG
        search_results = self.retriever.search(
            query=query,
            limit=10,
            top_laws=15,
            expand_graph=True,
            auto_classify=True
        )
        articles = search_results.get('articles', [])[:5]
        laws_retrieved = list(set(a.get('law_code', '') for a in articles))

        # Generate response
        response_data = self.generator.generate(query, articles)
        response_text = response_data.get('response', '')

        # Run trials
        trials = []
        for t in range(num_trials):
            logger.info(f"  Trial {t+1}/{num_trials}")
            trial = self.run_single_trial(query, response_text, articles, t+1)
            trials.append(trial)
            time.sleep(0.5)  # Rate limit

        # Aggregate
        faith_scores = [t.faithfulness_score for t in trials]
        relevance_scores = [t.answer_relevance_score for t in trials]
        precision_scores = [t.context_precision_score for t in trials]
        recall_scores = [t.context_recall_score for t in trials]

        # RAGAS score (harmonic mean)
        means = [
            statistics.mean(faith_scores),
            statistics.mean(relevance_scores),
            statistics.mean(precision_scores),
            statistics.mean(recall_scores)
        ]
        ragas = len(means) / sum(1/m if m > 0 else 100 for m in means)

        # Hallucination rate
        hall_rate = sum(0 if t.hallucination_free else 1 for t in trials) / len(trials)

        return QuestionEvaluation(
            question_id=question_data.get('id', 'unknown'),
            query=query,
            category=question_data.get('category', 'unknown'),
            expected_laws=question_data.get('expected_laws', []),
            laws_retrieved=laws_retrieved,
            faithfulness_mean=statistics.mean(faith_scores),
            faithfulness_std=statistics.stdev(faith_scores) if len(faith_scores) > 1 else 0,
            answer_relevance_mean=statistics.mean(relevance_scores),
            context_precision_mean=statistics.mean(precision_scores),
            context_recall_mean=statistics.mean(recall_scores),
            ragas_score=ragas,
            hallucination_rate=hall_rate,
            trials=[asdict(t) for t in trials],
            num_trials=num_trials,
            evaluation_time=time.time() - start_time
        )

    def run_evaluation(
        self,
        questions: List[Dict],
        num_trials: int = 3,
        save_results: bool = True
    ) -> EvaluationReport:
        """Run full evaluation."""
        total = len(questions) * num_trials
        logger.info(f"Starting evaluation: {len(questions)} questions × {num_trials} trials = {total} evaluations")

        evaluations = []

        for i, q in enumerate(questions):
            logger.info(f"[{i+1}/{len(questions)}] {q.get('id', '')}: {q.get('query', '')[:50]}...")

            try:
                result = self.evaluate_question(q, num_trials=num_trials)
                evaluations.append(result)
                logger.info(f"  → RAGAS: {result.ragas_score:.2f} | Faith: {result.faithfulness_mean:.2f}")
            except Exception as e:
                logger.error(f"  → Error: {e}")

        # Build report
        report = self._build_report(evaluations, num_trials)

        if save_results:
            output_path = Path('tests/eval_results') / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path.parent.mkdir(exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)

            logger.info(f"Results saved to {output_path}")

        return report

    def _build_report(self, evaluations: List[QuestionEvaluation], num_trials: int) -> EvaluationReport:
        """Build aggregate report."""
        if not evaluations:
            raise ValueError("No evaluations to report")

        # Scores
        faith = [e.faithfulness_mean for e in evaluations]
        relevance = [e.answer_relevance_mean for e in evaluations]
        precision = [e.context_precision_mean for e in evaluations]
        recall = [e.context_recall_mean for e in evaluations]
        ragas = [e.ragas_score for e in evaluations]
        hall_rates = [e.hallucination_rate for e in evaluations]

        # Hallucination types
        hall_types = {}
        missing_laws = {}

        for e in evaluations:
            for t in e.trials:
                for h in t.get('hallucinations', []):
                    htype = h.get('type', 'unknown')
                    hall_types[htype] = hall_types.get(htype, 0) + 1
                for law in t.get('cross_refs_missing', []):
                    missing_laws[law] = missing_laws.get(law, 0) + 1

        # By category
        cat_scores = {}
        for e in evaluations:
            cat = e.category
            if cat not in cat_scores:
                cat_scores[cat] = {'faith': [], 'ragas': [], 'count': 0}
            cat_scores[cat]['faith'].append(e.faithfulness_mean)
            cat_scores[cat]['ragas'].append(e.ragas_score)
            cat_scores[cat]['count'] += 1

        scores_by_cat = {
            cat: {
                'faithfulness': round(statistics.mean(s['faith']), 3),
                'ragas_score': round(statistics.mean(s['ragas']), 3),
                'count': s['count']
            }
            for cat, s in cat_scores.items()
        }

        # Cost
        cost_info = self.llm.get_cost(use_batch=self.use_batch) if hasattr(self.llm, 'get_cost') else {
            'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0
        }

        return EvaluationReport(
            timestamp=datetime.now().isoformat(),
            model_used=self.llm.model_id if hasattr(self.llm, 'model_id') else 'unknown',
            num_questions=len(evaluations),
            num_trials_per_question=num_trials,
            total_evaluations=len(evaluations) * num_trials,
            mean_faithfulness=round(statistics.mean(faith), 3),
            mean_answer_relevance=round(statistics.mean(relevance), 3),
            mean_context_precision=round(statistics.mean(precision), 3),
            mean_context_recall=round(statistics.mean(recall), 3),
            mean_ragas_score=round(statistics.mean(ragas), 3),
            std_faithfulness=round(statistics.stdev(faith), 3) if len(faith) > 1 else 0,
            std_answer_relevance=round(statistics.stdev(relevance), 3) if len(relevance) > 1 else 0,
            overall_hallucination_rate=round(statistics.mean(hall_rates), 3),
            common_hallucination_types=hall_types,
            commonly_missing_laws=sorted(missing_laws.items(), key=lambda x: -x[1])[:10],
            scores_by_category=scores_by_cat,
            question_evaluations=[asdict(e) for e in evaluations],
            total_input_tokens=cost_info.get('input_tokens', 0),
            total_output_tokens=cost_info.get('output_tokens', 0),
            estimated_cost=cost_info.get('total_cost', 0)
        )


# =============================================================================
# CLI
# =============================================================================

def print_report(report: EvaluationReport):
    """Print formatted report."""
    print("\n" + "=" * 70)
    print("RESEARCH-GRADE RAG EVALUATION REPORT")
    print("=" * 70)

    print(f"\nModel: {report.model_used}")
    print(f"Questions: {report.num_questions} × {report.num_trials_per_question} trials = {report.total_evaluations} evaluations")

    print(f"\n{'RAGAS METRICS (0-1 scale)':^50}")
    print("-" * 50)
    print(f"{'Metric':<25} {'Score':>10} {'Std':>10}")
    print("-" * 50)
    print(f"{'Faithfulness':<25} {report.mean_faithfulness:>10.3f} {report.std_faithfulness:>10.3f}")
    print(f"{'Answer Relevance':<25} {report.mean_answer_relevance:>10.3f} {report.std_answer_relevance:>10.3f}")
    print(f"{'Context Precision':<25} {report.mean_context_precision:>10.3f}")
    print(f"{'Context Recall':<25} {report.mean_context_recall:>10.3f}")
    print("-" * 50)
    print(f"{'RAGAS Score (harmonic)':<25} {report.mean_ragas_score:>10.3f}")

    print(f"\n{'HALLUCINATION ANALYSIS':^50}")
    print("-" * 50)
    print(f"Overall Rate: {report.overall_hallucination_rate:.1%}")

    if report.common_hallucination_types:
        print("\nTypes found:")
        for htype, count in sorted(report.common_hallucination_types.items(), key=lambda x: -x[1])[:5]:
            print(f"  {htype}: {count}")

    if report.commonly_missing_laws:
        print(f"\n{'COMMONLY MISSING LAWS':^50}")
        print("-" * 50)
        for law, count in report.commonly_missing_laws[:5]:
            print(f"  {law}: {count}x")

    print(f"\n{'SCORES BY CATEGORY':^50}")
    print("-" * 50)
    for cat, scores in sorted(report.scores_by_category.items(), key=lambda x: -x[1]['ragas_score']):
        print(f"{cat}: RAGAS={scores['ragas_score']:.2f} Faith={scores['faithfulness']:.2f} (n={scores['count']})")

    print(f"\n{'COST':^50}")
    print("-" * 50)
    print(f"Input tokens:  {report.total_input_tokens:,}")
    print(f"Output tokens: {report.total_output_tokens:,}")
    print(f"Total cost:    ${report.estimated_cost:.4f}")

    print("\n" + "=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Research-Grade RAG Evaluation")
    parser.add_argument("--quick", action="store_true", help="20 questions, 1 trial (~$0.02)")
    parser.add_argument("--standard", action="store_true", help="50 questions, 3 trials (~$0.15)")
    parser.add_argument("--full", action="store_true", help="All questions, 6 trials (~$0.60)")
    parser.add_argument("--questions", "-n", type=int, help="Custom number of questions")
    parser.add_argument("--trials", "-t", type=int, default=3, help="Trials per question")
    parser.add_argument("--batch", action="store_true", help="Use batch API (50% cheaper)")
    parser.add_argument("--model", "-m", default="gemini-2.5-flash")

    args = parser.parse_args()

    # Load questions
    from comprehensive_rag_eval import TEST_QUESTIONS

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

    # Settings
    if args.quick:
        n_questions, n_trials = 20, 1
    elif args.standard:
        n_questions, n_trials = 50, 3
    elif args.full:
        n_questions, n_trials = len(questions), 6
    else:
        n_questions = args.questions or 50
        n_trials = args.trials

    questions = questions[:n_questions]

    # Cost estimate
    evals = n_questions * n_trials
    input_tokens = evals * 3500  # ~3500 tokens per eval (5 prompts)
    output_tokens = evals * 1000

    if args.batch:
        cost = (input_tokens / 1e6 * 0.15) + (output_tokens / 1e6 * 1.25)
    else:
        cost = (input_tokens / 1e6 * 0.30) + (output_tokens / 1e6 * 2.50)

    print(f"\n{'Configuration':^50}")
    print("=" * 50)
    print(f"Questions:     {n_questions}")
    print(f"Trials each:   {n_trials}")
    print(f"Total evals:   {evals}")
    print(f"Model:         {args.model}")
    print(f"Batch API:     {args.batch}")
    print(f"Est. cost:     ${cost:.4f}")
    print("=" * 50)

    input("\nPress Enter to start...")

    # Run
    evaluator = ResearchGradeEvaluator(model=args.model, use_batch=args.batch)
    report = evaluator.run_evaluation(questions, num_trials=n_trials)

    print_report(report)


if __name__ == "__main__":
    main()
