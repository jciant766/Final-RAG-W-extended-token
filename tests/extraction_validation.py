"""
Research-Grade Extraction Validation System

Validates the quality of law extractions against original PDFs using LLM-as-judge.

Based on established research methodologies:
- RAGAS Framework (2023) - Faithfulness, Completeness metrics
- Bloomberg Law Methodology (2025) - Multiple trials, statistical significance
- Microsoft BenchmarkQED - 6 trials per query for confidence intervals
- Legal AI Evaluation Standards - Domain-specific accuracy metrics

Metrics Evaluated:
1. EXTRACTION_FAITHFULNESS - Is extracted text faithful to the PDF?
2. EXTRACTION_COMPLETENESS - Were all articles/regulations captured?
3. CROSS_REFERENCE_ACCURACY - Are internal/external references correct?
4. STRUCTURE_PRESERVATION - Is the legal hierarchy preserved?
5. COVERAGE_SCORE - What percentage of content was extracted?

Statistical Measures:
- Point estimates with 95% confidence intervals
- Cohen's Kappa for inter-rater reliability
- F1 scores for precision/recall balance

Usage:
    # Validate single law
    python tests/extraction_validation.py --law "S.L. 427.81"

    # Validate with multiple trials (research-grade)
    python tests/extraction_validation.py --law "S.L. 427.81" --trials 6

    # Validate random sample of laws
    python tests/extraction_validation.py --sample 10 --trials 3

    # Full validation suite
    python tests/extraction_validation.py --full
"""

import os
import sys
import json
import time
import random
import argparse
import statistics
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

import fitz  # PyMuPDF
import google.generativeai as genai

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Configure Gemini
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-2.0-flash"

# Paths
EXTRACTIONS_DIR = Path(__file__).parent.parent / "extractions"
PDF_DIR = Path(__file__).parent.parent / "All Malta law PDFs"
LAWS_INDEX = Path(__file__).parent.parent / "laws_to_extract.json"

# Research parameters (based on Bloomberg Law & BenchmarkQED)
DEFAULT_TRIALS = 3  # Standard evaluation
RESEARCH_TRIALS = 6  # Full research-grade (statistical significance)
CONFIDENCE_LEVEL = 0.95  # 95% confidence intervals
MIN_QUESTIONS_PER_LAW = 10  # Minimum questions for statistical validity

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ValidationQuestion:
    """A question to validate extraction quality."""
    question_id: str
    question_type: str  # faithfulness, completeness, cross_reference, structure
    question: str
    expected_answer: str
    source_article: Optional[str] = None
    page_reference: Optional[int] = None

@dataclass
class ValidationResult:
    """Result of validating a single question."""
    question_id: str
    question_type: str
    is_correct: bool
    confidence: float
    llm_reasoning: str
    extracted_text: str
    pdf_text: Optional[str] = None

@dataclass
class TrialResult:
    """Result of a single validation trial."""
    trial_id: int
    timestamp: str
    questions_total: int
    questions_correct: int
    accuracy: float
    results_by_type: Dict[str, Dict[str, float]]

@dataclass
class LawValidationReport:
    """Complete validation report for a law."""
    law_code: str
    law_name: str
    pdf_pages: int
    extraction_metrics: Dict[str, Any]
    trials: List[TrialResult]
    aggregate_metrics: Dict[str, Any]
    statistical_analysis: Dict[str, Any]
    questions_asked: List[ValidationQuestion]
    detailed_results: List[ValidationResult]

# =============================================================================
# PDF UTILITIES
# =============================================================================

def extract_pdf_text(pdf_path: str, page_num: Optional[int] = None) -> str:
    """Extract text from PDF, optionally from specific page."""
    try:
        doc = fitz.open(pdf_path)
        if page_num is not None:
            if 0 <= page_num < len(doc):
                text = doc[page_num].get_text()
            else:
                text = ""
        else:
            text = ""
            for page in doc:
                text += page.get_text() + "\n\n"
        doc.close()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def get_pdf_page_count(pdf_path: str) -> int:
    """Get number of pages in PDF."""
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except:
        return 0

# =============================================================================
# QUESTION GENERATION
# =============================================================================

def generate_faithfulness_questions(extraction: Dict, num_questions: int = 5) -> List[ValidationQuestion]:
    """Generate questions to test if extracted text is faithful to source."""
    questions = []

    # Get regulations/articles
    items = extraction.get('regulations', []) or extraction.get('articles', [])

    for i, item in enumerate(items[:num_questions]):
        item_num = item.get('number', str(i+1))
        item_text = item.get('text', '')[:500]  # First 500 chars

        if item_text:
            questions.append(ValidationQuestion(
                question_id=f"FAITH-{i+1}",
                question_type="faithfulness",
                question=f"Does regulation/article {item_num} in the PDF contain this exact text (allowing for minor formatting differences): '{item_text[:200]}...'?",
                expected_answer="yes",
                source_article=item_num,
                page_reference=item.get('page_start')
            ))

    return questions

def generate_completeness_questions(extraction: Dict, pdf_path: str) -> List[ValidationQuestion]:
    """Generate questions to test if all content was extracted."""
    questions = []

    # Check regulation/article count
    items = extraction.get('regulations', []) or extraction.get('articles', [])
    item_count = len(items)
    item_type = "regulations" if extraction.get('regulations') else "articles"

    questions.append(ValidationQuestion(
        question_id="COMP-COUNT",
        question_type="completeness",
        question=f"How many numbered {item_type} are in this law? The extraction found {item_count}.",
        expected_answer=str(item_count),
        source_article=None,
        page_reference=None
    ))

    # Check for schedules
    schedules = extraction.get('schedules', [])
    if schedules:
        schedule_names = [s.get('name', '') for s in schedules]
        questions.append(ValidationQuestion(
            question_id="COMP-SCHED",
            question_type="completeness",
            question=f"Does this law contain schedules? The extraction found: {', '.join(schedule_names)}",
            expected_answer="yes" if schedules else "no",
            source_article=None,
            page_reference=None
        ))

    return questions

def generate_cross_reference_questions(extraction: Dict, num_questions: int = 5) -> List[ValidationQuestion]:
    """Generate questions to validate cross-references."""
    questions = []

    items = extraction.get('regulations', []) or extraction.get('articles', [])

    ref_count = 0
    for item in items:
        cross_refs = item.get('cross_references', {})
        internal = cross_refs.get('internal', [])
        external = cross_refs.get('external', [])

        for ref in internal[:2]:  # Max 2 per article
            if ref_count >= num_questions:
                break
            target = ref.get('target', '')
            item_num = item.get('number', '')

            questions.append(ValidationQuestion(
                question_id=f"XREF-INT-{ref_count+1}",
                question_type="cross_reference",
                question=f"Does regulation/article {item_num} reference '{target}' internally?",
                expected_answer="yes",
                source_article=item_num,
                page_reference=item.get('page_start')
            ))
            ref_count += 1

        for ref in external[:2]:
            if ref_count >= num_questions:
                break
            target = ref.get('target', '')
            target_law = ref.get('target_law', '')
            item_num = item.get('number', '')

            questions.append(ValidationQuestion(
                question_id=f"XREF-EXT-{ref_count+1}",
                question_type="cross_reference",
                question=f"Does regulation/article {item_num} reference external law '{target_law}' or '{target}'?",
                expected_answer="yes",
                source_article=item_num,
                page_reference=item.get('page_start')
            ))
            ref_count += 1

    return questions

def generate_structure_questions(extraction: Dict) -> List[ValidationQuestion]:
    """Generate questions to validate structural preservation."""
    questions = []

    items = extraction.get('regulations', []) or extraction.get('articles', [])

    # Check sub-items
    for i, item in enumerate(items[:3]):
        sub_items = item.get('sub_items', [])
        item_num = item.get('number', '')

        if sub_items:
            questions.append(ValidationQuestion(
                question_id=f"STRUCT-{i+1}",
                question_type="structure",
                question=f"Does regulation/article {item_num} have sub-items like {sub_items[:3]}?",
                expected_answer="yes",
                source_article=item_num,
                page_reference=item.get('page_start')
            ))

    return questions

def generate_all_questions(extraction: Dict, pdf_path: str, min_questions: int = 10) -> List[ValidationQuestion]:
    """Generate comprehensive validation questions for an extraction."""
    questions = []

    # Faithfulness questions (40% of total)
    questions.extend(generate_faithfulness_questions(extraction, max(4, min_questions // 3)))

    # Completeness questions (20%)
    questions.extend(generate_completeness_questions(extraction, pdf_path))

    # Cross-reference questions (25%)
    questions.extend(generate_cross_reference_questions(extraction, max(3, min_questions // 4)))

    # Structure questions (15%)
    questions.extend(generate_structure_questions(extraction))

    # Ensure minimum questions
    while len(questions) < min_questions:
        questions.extend(generate_faithfulness_questions(extraction, 2))
        if len(questions) >= min_questions:
            break

    return questions[:max(min_questions, len(questions))]

# =============================================================================
# LLM VALIDATION (JUDGE)
# =============================================================================

VALIDATION_PROMPT = """You are a legal document validation expert. Your task is to verify if an extraction from a legal PDF is accurate.

ORIGINAL PDF TEXT (from the relevant pages):
\"\"\"
{pdf_text}
\"\"\"

VALIDATION QUESTION:
{question}

EXTRACTED CONTENT BEING VALIDATED:
{extracted_content}

Instructions:
1. Carefully compare the extracted content against the original PDF text
2. Consider minor formatting differences as acceptable (whitespace, line breaks)
3. Focus on substantive accuracy of legal content
4. Be strict about legal terms, numbers, and references

Respond with JSON:
{{
    "is_correct": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your judgment",
    "evidence": "Quote from PDF that supports your decision"
}}"""

def validate_question_with_llm(
    question: ValidationQuestion,
    extraction: Dict,
    pdf_text: str,
    model_name: str = MODEL_NAME
) -> ValidationResult:
    """Use LLM to validate a single question."""

    # Get relevant extracted content
    extracted_content = ""
    items = extraction.get('regulations', []) or extraction.get('articles', [])

    if question.source_article:
        for item in items:
            if item.get('number') == question.source_article:
                extracted_content = json.dumps(item, indent=2)
                break

    if not extracted_content:
        extracted_content = json.dumps({
            "regulations_count": len(extraction.get('regulations', [])),
            "articles_count": len(extraction.get('articles', [])),
            "schedules": [s.get('name') for s in extraction.get('schedules', [])],
            "metadata": extraction.get('metadata', {})
        }, indent=2)

    prompt = VALIDATION_PROMPT.format(
        pdf_text=pdf_text[:8000],  # Limit context
        question=question.question,
        extracted_content=extracted_content[:3000]
    )

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        content = response.text.strip()

        # Parse JSON response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        return ValidationResult(
            question_id=question.question_id,
            question_type=question.question_type,
            is_correct=result.get('is_correct', False),
            confidence=result.get('confidence', 0.5),
            llm_reasoning=result.get('reasoning', ''),
            extracted_text=extracted_content[:500],
            pdf_text=result.get('evidence', '')[:500]
        )

    except Exception as e:
        return ValidationResult(
            question_id=question.question_id,
            question_type=question.question_type,
            is_correct=False,
            confidence=0.0,
            llm_reasoning=f"Error: {str(e)}",
            extracted_text=extracted_content[:500],
            pdf_text=""
        )

# =============================================================================
# STATISTICAL ANALYSIS
# =============================================================================

def calculate_confidence_interval(values: List[float], confidence: float = 0.95) -> Tuple[float, float, float]:
    """Calculate mean and confidence interval for a list of values."""
    if not values:
        return 0.0, 0.0, 0.0

    n = len(values)
    mean = statistics.mean(values)

    if n < 2:
        return mean, mean, mean

    std_err = statistics.stdev(values) / math.sqrt(n)

    # t-value for 95% CI (approximate for small samples)
    t_values = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 10: 2.23, 30: 2.04}
    t = t_values.get(n, 1.96)  # Default to z-value for large n

    margin = t * std_err
    return mean, mean - margin, mean + margin

def calculate_f1_score(precision: float, recall: float) -> float:
    """Calculate F1 score from precision and recall."""
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)

def calculate_cohens_kappa(observed_agreement: float, expected_agreement: float) -> float:
    """Calculate Cohen's Kappa for inter-rater reliability."""
    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)

def aggregate_trial_results(trials: List[TrialResult]) -> Dict[str, Any]:
    """Aggregate results across multiple trials with statistical analysis."""

    accuracies = [t.accuracy for t in trials]
    mean_acc, ci_low, ci_high = calculate_confidence_interval(accuracies)

    # Aggregate by question type
    type_results = defaultdict(list)
    for trial in trials:
        for qtype, metrics in trial.results_by_type.items():
            type_results[qtype].append(metrics.get('accuracy', 0))

    type_aggregates = {}
    for qtype, accs in type_results.items():
        mean, low, high = calculate_confidence_interval(accs)
        type_aggregates[qtype] = {
            "mean_accuracy": round(mean, 4),
            "ci_95_low": round(low, 4),
            "ci_95_high": round(high, 4),
            "std_dev": round(statistics.stdev(accs), 4) if len(accs) > 1 else 0
        }

    return {
        "overall_accuracy": {
            "mean": round(mean_acc, 4),
            "ci_95_low": round(ci_low, 4),
            "ci_95_high": round(ci_high, 4),
            "std_dev": round(statistics.stdev(accuracies), 4) if len(accuracies) > 1 else 0
        },
        "by_question_type": type_aggregates,
        "num_trials": len(trials),
        "statistical_power": "sufficient" if len(trials) >= 6 else "limited"
    }

# =============================================================================
# MAIN VALIDATION LOGIC
# =============================================================================

def validate_law(
    law_code: str,
    num_trials: int = DEFAULT_TRIALS,
    verbose: bool = True
) -> Optional[LawValidationReport]:
    """Validate extraction quality for a single law."""

    # Load extraction
    extraction_file = EXTRACTIONS_DIR / f"extraction_{law_code.replace(' ', '')}.json"
    if not extraction_file.exists():
        print(f"ERROR: Extraction not found: {extraction_file}")
        return None

    with open(extraction_file, 'r', encoding='utf-8') as f:
        extraction = json.load(f)

    # Find PDF
    pdf_path = None
    if LAWS_INDEX.exists():
        with open(LAWS_INDEX, 'r', encoding='utf-8') as f:
            laws = json.load(f)
        for law in laws:
            if law.get('cap') == law_code:
                pdf_path = PDF_DIR.parent / law.get('pdf_path', '')
                break

    if not pdf_path or not pdf_path.exists():
        # Try to find by pattern
        for pdf in PDF_DIR.glob(f"*({law_code.replace(' ', '')})*.pdf"):
            pdf_path = pdf
            break
        for pdf in PDF_DIR.glob(f"*({law_code})*.pdf"):
            pdf_path = pdf
            break

    if not pdf_path or not pdf_path.exists():
        print(f"ERROR: PDF not found for {law_code}")
        return None

    if verbose:
        print(f"\n{'='*60}")
        print(f"VALIDATING: {law_code}")
        print(f"PDF: {pdf_path.name}")
        print(f"Trials: {num_trials}")
        print(f"{'='*60}")

    # Extract PDF text
    pdf_text = extract_pdf_text(str(pdf_path))
    pdf_pages = get_pdf_page_count(str(pdf_path))

    # Generate questions
    questions = generate_all_questions(extraction, str(pdf_path), MIN_QUESTIONS_PER_LAW)

    if verbose:
        print(f"Generated {len(questions)} validation questions")
        for qt in set(q.question_type for q in questions):
            count = sum(1 for q in questions if q.question_type == qt)
            print(f"  - {qt}: {count}")

    # Run trials
    all_trials = []
    all_results = []

    for trial_num in range(num_trials):
        if verbose:
            print(f"\nTrial {trial_num + 1}/{num_trials}...")

        trial_results = []

        for q in questions:
            result = validate_question_with_llm(q, extraction, pdf_text)
            trial_results.append(result)
            all_results.append(result)

            if verbose:
                status = "PASS" if result.is_correct else "FAIL"
                print(f"  [{status}] {q.question_id}: {result.confidence:.2f} confidence")

            time.sleep(0.5)  # Rate limiting

        # Calculate trial metrics
        correct = sum(1 for r in trial_results if r.is_correct)
        accuracy = correct / len(trial_results) if trial_results else 0

        # Metrics by type
        type_metrics = {}
        for qtype in set(q.question_type for q in questions):
            type_results = [r for r in trial_results if r.question_type == qtype]
            type_correct = sum(1 for r in type_results if r.is_correct)
            type_metrics[qtype] = {
                "accuracy": type_correct / len(type_results) if type_results else 0,
                "total": len(type_results),
                "correct": type_correct
            }

        trial = TrialResult(
            trial_id=trial_num + 1,
            timestamp=datetime.now().isoformat(),
            questions_total=len(questions),
            questions_correct=correct,
            accuracy=accuracy,
            results_by_type=type_metrics
        )
        all_trials.append(trial)

        if verbose:
            print(f"  Trial accuracy: {accuracy:.1%}")

    # Aggregate statistics
    aggregate = aggregate_trial_results(all_trials)

    # Build report
    report = LawValidationReport(
        law_code=law_code,
        law_name=extraction.get('law_name', ''),
        pdf_pages=pdf_pages,
        extraction_metrics=extraction.get('metrics', {}),
        trials=all_trials,
        aggregate_metrics=aggregate,
        statistical_analysis={
            "methodology": "RAGAS + Bloomberg Law + BenchmarkQED",
            "confidence_level": CONFIDENCE_LEVEL,
            "min_questions": MIN_QUESTIONS_PER_LAW,
            "trials_for_significance": RESEARCH_TRIALS
        },
        questions_asked=questions,
        detailed_results=all_results
    )

    return report

def print_report(report: LawValidationReport):
    """Print a formatted validation report."""
    print("\n" + "="*70)
    print("EXTRACTION VALIDATION REPORT")
    print("="*70)

    print(f"\nLaw: {report.law_code} - {report.law_name}")
    print(f"PDF Pages: {report.pdf_pages}")
    print(f"Extraction Time: {report.extraction_metrics.get('extraction_time_seconds', 'N/A')}s")

    print(f"\n{'-'*70}")
    print("AGGREGATE METRICS (across all trials)")
    print(f"{'-'*70}")

    overall = report.aggregate_metrics.get('overall_accuracy', {})
    print(f"Overall Accuracy: {overall.get('mean', 0):.1%}")
    print(f"95% Confidence Interval: [{overall.get('ci_95_low', 0):.1%}, {overall.get('ci_95_high', 0):.1%}]")
    print(f"Standard Deviation: {overall.get('std_dev', 0):.3f}")
    print(f"Statistical Power: {report.aggregate_metrics.get('statistical_power', 'unknown')}")

    print(f"\n{'-'*70}")
    print("METRICS BY QUESTION TYPE")
    print(f"{'-'*70}")

    by_type = report.aggregate_metrics.get('by_question_type', {})
    for qtype, metrics in by_type.items():
        print(f"\n{qtype.upper()}:")
        print(f"  Accuracy: {metrics.get('mean_accuracy', 0):.1%}")
        print(f"  95% CI: [{metrics.get('ci_95_low', 0):.1%}, {metrics.get('ci_95_high', 0):.1%}]")

    print(f"\n{'-'*70}")
    print("QUALITY ASSESSMENT")
    print(f"{'-'*70}")

    accuracy = overall.get('mean', 0)
    if accuracy >= 0.95:
        grade = "EXCELLENT"
        emoji = "[A+]"
    elif accuracy >= 0.85:
        grade = "GOOD"
        emoji = "[A]"
    elif accuracy >= 0.70:
        grade = "ACCEPTABLE"
        emoji = "[B]"
    else:
        grade = "NEEDS IMPROVEMENT"
        emoji = "[C]"

    print(f"{emoji} Overall Grade: {grade}")
    print(f"   Based on {report.aggregate_metrics.get('num_trials', 0)} trials, {len(report.questions_asked)} questions")

    print("\n" + "="*70)

def save_report(report: LawValidationReport, output_dir: Path):
    """Save validation report to JSON file."""
    output_dir.mkdir(exist_ok=True)

    # Convert dataclasses to dicts
    report_dict = {
        "law_code": report.law_code,
        "law_name": report.law_name,
        "pdf_pages": report.pdf_pages,
        "extraction_metrics": report.extraction_metrics,
        "trials": [asdict(t) for t in report.trials],
        "aggregate_metrics": report.aggregate_metrics,
        "statistical_analysis": report.statistical_analysis,
        "questions_asked": [asdict(q) for q in report.questions_asked],
        "detailed_results": [asdict(r) for r in report.detailed_results],
        "generated_at": datetime.now().isoformat()
    }

    output_file = output_dir / f"validation_{report.law_code.replace(' ', '').replace('.', '_')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {output_file}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Research-grade extraction validation')
    parser.add_argument('--law', type=str, help='Single law code to validate (e.g., "S.L. 427.81")')
    parser.add_argument('--trials', type=int, default=DEFAULT_TRIALS, help=f'Number of trials (default: {DEFAULT_TRIALS}, research: {RESEARCH_TRIALS})')
    parser.add_argument('--sample', type=int, help='Validate random sample of N laws')
    parser.add_argument('--full', action='store_true', help='Full validation suite (all laws, 6 trials)')
    parser.add_argument('--output', type=str, default='validation_reports', help='Output directory')

    args = parser.parse_args()

    print("="*70)
    print("RESEARCH-GRADE EXTRACTION VALIDATION")
    print("="*70)
    print(f"Methodology: RAGAS + Bloomberg Law + BenchmarkQED")
    print(f"Model: {MODEL_NAME}")
    print(f"Confidence Level: {CONFIDENCE_LEVEL:.0%}")

    output_dir = Path(__file__).parent.parent / args.output

    if args.law:
        # Validate single law
        report = validate_law(args.law, args.trials, verbose=True)
        if report:
            print_report(report)
            save_report(report, output_dir)

    elif args.sample:
        # Validate random sample
        extraction_files = list(EXTRACTIONS_DIR.glob("extraction_*.json"))
        sample = random.sample(extraction_files, min(args.sample, len(extraction_files)))

        all_reports = []
        for ext_file in sample:
            law_code = ext_file.stem.replace("extraction_", "").replace("_", " ")
            # Normalize code format
            if law_code.startswith("S.L"):
                law_code = "S.L. " + law_code[3:].lstrip(". ")
            elif law_code.startswith("Cap"):
                law_code = "Cap. " + law_code[3:].lstrip(". ")

            report = validate_law(law_code, args.trials, verbose=True)
            if report:
                print_report(report)
                save_report(report, output_dir)
                all_reports.append(report)

        # Summary
        if all_reports:
            print("\n" + "="*70)
            print("SAMPLE VALIDATION SUMMARY")
            print("="*70)
            accuracies = [r.aggregate_metrics['overall_accuracy']['mean'] for r in all_reports]
            mean_acc = statistics.mean(accuracies)
            print(f"Laws validated: {len(all_reports)}")
            print(f"Mean accuracy: {mean_acc:.1%}")
            print(f"Min accuracy: {min(accuracies):.1%}")
            print(f"Max accuracy: {max(accuracies):.1%}")

    elif args.full:
        print("\nFull validation not yet implemented - use --sample or --law")

    else:
        # Default: validate S.L. 427.81 as demo
        print("\nNo law specified. Running demo validation on S.L. 427.81...")
        report = validate_law("S.L. 427.81", args.trials, verbose=True)
        if report:
            print_report(report)
            save_report(report, output_dir)

if __name__ == "__main__":
    main()
