"""
RAG Test Questions for Maltese Law System

This module contains test questions designed to expose common RAG failure modes:
1. Synonym/Terminology Mismatches
2. Hierarchical Retrieval Gaps (Parent Act vs Subsidiary Legislation)
3. Cross-Reference Blindness
4. Schedule/Appendix Retrieval
5. Multi-hop Reasoning

Each test question includes:
- The query (how a user would naturally ask)
- Expected sources (what SHOULD be retrieved)
- Failure mode being tested
- Synonyms/variants that should match
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class FailureMode(Enum):
    SYNONYM_MISMATCH = "synonym_mismatch"
    HIERARCHICAL_GAP = "hierarchical_gap"
    CROSS_REFERENCE = "cross_reference"
    SCHEDULE_APPENDIX = "schedule_appendix"
    MULTI_HOP = "multi_hop"
    TEMPORAL = "temporal"
    ABBREVIATION = "abbreviation"


@dataclass
class RAGTestQuestion:
    """A test question for evaluating RAG retrieval quality."""

    id: str
    query: str  # How a user would naturally ask
    failure_mode: FailureMode
    expected_laws: List[str]  # Law codes that SHOULD be retrieved
    expected_articles: List[str] = field(default_factory=list)  # Specific articles
    synonyms: List[str] = field(default_factory=list)  # Terms that should match
    legal_terms: List[str] = field(default_factory=list)  # Actual legal terminology
    description: str = ""
    difficulty: str = "medium"  # easy, medium, hard


# =============================================================================
# TEST SUITE 1: SYNONYM/TERMINOLOGY MISMATCHES
# =============================================================================

SYNONYM_TESTS = [
    RAGTestQuestion(
        id="SYN-001",
        query="What are the rules for orange traffic lights in Malta?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["S.L. 65.11", "Cap. 65"],
        expected_articles=["S.L. 65.11 Art. 50", "S.L. 65.11 Art. 51"],
        synonyms=["orange light", "yellow light", "caution light"],
        legal_terms=["amber light", "amber signal"],
        description="Users say 'orange' but law says 'amber'",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="SYN-002",
        query="What happens if I get caught drunk driving?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["Cap. 65", "S.L. 65.11"],
        synonyms=["drunk driving", "DUI", "DWI", "driving drunk", "intoxicated driving"],
        legal_terms=["driving under the influence", "driving while intoxicated",
                     "blood alcohol concentration", "breath test"],
        description="Common speech vs legal terminology for alcohol-related driving",
        difficulty="easy"
    ),
    RAGTestQuestion(
        id="SYN-003",
        query="How do I evict a tenant who won't pay rent?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["Cap. 69", "Cap. 12"],  # Civil Code, Housing
        synonyms=["evict", "kick out", "remove tenant", "get rid of tenant"],
        legal_terms=["termination of lease", "ejectment", "repossession",
                     "rescission of contract"],
        description="Colloquial 'evict' vs legal termination procedures",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="SYN-004",
        query="Can my employer fire me without notice?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["Cap. 452", "S.L. 452.81"],  # Employment and Industrial Relations
        synonyms=["fire", "sack", "let go", "terminate", "dismiss"],
        legal_terms=["dismissal", "termination of employment", "summary dismissal",
                     "unfair dismissal", "redundancy"],
        description="Colloquial 'fire' vs legal employment termination terms",
        difficulty="easy"
    ),
    RAGTestQuestion(
        id="SYN-005",
        query="What are the rules about jaywalking in Malta?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["Cap. 65", "S.L. 65.11"],
        synonyms=["jaywalking", "crossing the road illegally"],
        legal_terms=["pedestrian crossing", "crossing other than at pedestrian crossing",
                     "pedestrian regulations"],
        description="American term 'jaywalking' not used in Maltese law",
        difficulty="hard"
    ),
    RAGTestQuestion(
        id="SYN-006",
        query="How do I start a company in Malta?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["Cap. 386"],  # Companies Act
        synonyms=["start a company", "open a business", "create a company",
                  "set up a business", "register a company"],
        legal_terms=["incorporation", "formation of company", "registration of company",
                     "memorandum and articles of association"],
        description="Casual 'start a company' vs legal incorporation terms",
        difficulty="easy"
    ),
    RAGTestQuestion(
        id="SYN-007",
        query="What are the fines for speeding in Malta?",
        failure_mode=FailureMode.SYNONYM_MISMATCH,
        expected_laws=["S.L. 65.11", "Cap. 65"],
        synonyms=["speeding", "going too fast", "driving too fast"],
        legal_terms=["exceeding speed limit", "speed restrictions",
                     "contravention of speed limit"],
        description="Common 'speeding' vs legal terminology",
        difficulty="easy"
    ),
]


# =============================================================================
# TEST SUITE 2: HIERARCHICAL RETRIEVAL GAPS
# =============================================================================

HIERARCHICAL_TESTS = [
    RAGTestQuestion(
        id="HIER-001",
        query="What are all the traffic regulations in Malta?",
        failure_mode=FailureMode.HIERARCHICAL_GAP,
        expected_laws=["Cap. 65", "S.L. 65.11", "S.L. 65.12", "S.L. 65.05"],
        description="Should retrieve parent Cap. 65 AND all subsidiary S.L. 65.xx",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="HIER-002",
        query="What does the Companies Act say about directors?",
        failure_mode=FailureMode.HIERARCHICAL_GAP,
        expected_laws=["Cap. 386"],  # Plus any relevant S.L.
        description="Should find Cap. 386 plus any subsidiary legislation on directors",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="HIER-003",
        query="What are the rules for importing goods into Malta?",
        failure_mode=FailureMode.HIERARCHICAL_GAP,
        expected_laws=["Cap. 37", "S.L. 37.01"],  # Customs Ordinance
        description="Should find Customs Ordinance and subsidiary import regulations",
        difficulty="hard"
    ),
    RAGTestQuestion(
        id="HIER-004",
        query="What does Maltese law say about data protection?",
        failure_mode=FailureMode.HIERARCHICAL_GAP,
        expected_laws=["Cap. 586", "S.L. 586.01"],  # Data Protection Act
        description="Should find DPA and all GDPR-related subsidiary legislation",
        difficulty="medium"
    ),
]


# =============================================================================
# TEST SUITE 3: CROSS-REFERENCE BLINDNESS
# =============================================================================

CROSS_REFERENCE_TESTS = [
    RAGTestQuestion(
        id="XREF-001",
        query="What penalties apply to traffic offenses mentioned in the Second Schedule?",
        failure_mode=FailureMode.CROSS_REFERENCE,
        expected_laws=["Cap. 65"],
        expected_articles=["Cap. 65 Second Schedule"],
        description="Article references Second Schedule - should follow that reference",
        difficulty="hard"
    ),
    RAGTestQuestion(
        id="XREF-002",
        query="What are the penalties under Article 338 of the Criminal Code?",
        failure_mode=FailureMode.CROSS_REFERENCE,
        expected_laws=["Cap. 9"],  # Criminal Code
        expected_articles=["Cap. 9 Art. 338"],
        description="Direct article reference - should find and follow cross-refs",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="XREF-003",
        query="What does 'as prescribed by regulations' mean for vehicle registration?",
        failure_mode=FailureMode.CROSS_REFERENCE,
        expected_laws=["Cap. 65", "S.L. 65.11"],
        description="Vague reference to regulations - should find the actual regulations",
        difficulty="hard"
    ),
]


# =============================================================================
# TEST SUITE 4: SCHEDULE/APPENDIX RETRIEVAL
# =============================================================================

SCHEDULE_TESTS = [
    RAGTestQuestion(
        id="SCHED-001",
        query="What are the specific fines for traffic violations?",
        failure_mode=FailureMode.SCHEDULE_APPENDIX,
        expected_laws=["Cap. 65", "S.L. 65.11"],
        description="Fine amounts often in Schedules, not main articles",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="SCHED-002",
        query="What documents are needed for company registration?",
        failure_mode=FailureMode.SCHEDULE_APPENDIX,
        expected_laws=["Cap. 386"],
        description="Forms and document lists often in Schedules",
        difficulty="medium"
    ),
    RAGTestQuestion(
        id="SCHED-003",
        query="What are the fee amounts for court proceedings?",
        failure_mode=FailureMode.SCHEDULE_APPENDIX,
        expected_laws=["Cap. 12"],  # Code of Organization and Civil Procedure
        description="Fee schedules are literally in schedule tables",
        difficulty="hard"
    ),
]


# =============================================================================
# TEST SUITE 5: MULTI-HOP REASONING
# =============================================================================

MULTI_HOP_TESTS = [
    RAGTestQuestion(
        id="MULTI-001",
        query="If I cause an accident while running a red light, what are ALL the penalties?",
        failure_mode=FailureMode.MULTI_HOP,
        expected_laws=["Cap. 65", "Cap. 9", "S.L. 65.11"],
        description="Requires combining traffic law + criminal law + injury provisions",
        difficulty="hard"
    ),
    RAGTestQuestion(
        id="MULTI-002",
        query="Can a company director be personally liable for company debts?",
        failure_mode=FailureMode.MULTI_HOP,
        expected_laws=["Cap. 386", "Cap. 12"],
        description="Requires finding director duties + liability provisions + exceptions",
        difficulty="hard"
    ),
    RAGTestQuestion(
        id="MULTI-003",
        query="What happens if I'm caught driving without insurance AND speeding?",
        failure_mode=FailureMode.MULTI_HOP,
        expected_laws=["Cap. 65", "S.L. 65.11", "Cap. 104"],  # Motor Vehicle Insurance
        description="Multiple concurrent offenses - need to find all applicable laws",
        difficulty="hard"
    ),
]


# =============================================================================
# TEST SUITE 6: ABBREVIATION/CODE TESTS
# =============================================================================

ABBREVIATION_TESTS = [
    RAGTestQuestion(
        id="ABBR-001",
        query="What does CAP 65 say about parking?",
        failure_mode=FailureMode.ABBREVIATION,
        expected_laws=["Cap. 65"],
        synonyms=["CAP 65", "CAP65", "Cap 65", "Cap. 65", "Chapter 65"],
        description="Users may write chapter codes in various formats",
        difficulty="easy"
    ),
    RAGTestQuestion(
        id="ABBR-002",
        query="What is SL 65.11?",
        failure_mode=FailureMode.ABBREVIATION,
        expected_laws=["S.L. 65.11"],
        synonyms=["SL 65.11", "SL65.11", "S.L.65.11", "S.L. 65.11"],
        description="Subsidiary legislation code format variations",
        difficulty="easy"
    ),
    RAGTestQuestion(
        id="ABBR-003",
        query="What does the COCP say about appeals?",
        failure_mode=FailureMode.ABBREVIATION,
        expected_laws=["Cap. 12"],
        synonyms=["COCP", "Code of Organization and Civil Procedure"],
        description="Common abbreviation for civil procedure code",
        difficulty="medium"
    ),
]


# =============================================================================
# ALL TEST QUESTIONS
# =============================================================================

ALL_TEST_QUESTIONS = (
    SYNONYM_TESTS +
    HIERARCHICAL_TESTS +
    CROSS_REFERENCE_TESTS +
    SCHEDULE_TESTS +
    MULTI_HOP_TESTS +
    ABBREVIATION_TESTS
)


# =============================================================================
# LEGAL SYNONYM DICTIONARY (for query expansion)
# =============================================================================

MALTESE_LEGAL_SYNONYMS = {
    # Traffic terms
    "orange light": ["amber light", "amber signal", "yellow light"],
    "amber light": ["orange light", "yellow light", "caution light"],
    "drunk driving": ["driving under the influence", "DUI", "intoxicated driving",
                      "driving while intoxicated", "drink driving"],
    "speeding": ["exceeding speed limit", "speed violation", "driving too fast"],
    "jaywalking": ["crossing illegally", "pedestrian violation",
                   "crossing other than at pedestrian crossing"],
    "traffic ticket": ["contravention notice", "fixed penalty notice", "traffic fine"],

    # Employment terms
    "fire": ["dismiss", "terminate employment", "termination", "dismissal"],
    "fired": ["dismissed", "terminated", "let go", "sacked"],
    "quit": ["resign", "resignation", "voluntary termination"],
    "wages": ["remuneration", "salary", "pay", "compensation"],

    # Housing/Property terms
    "evict": ["ejectment", "repossession", "termination of lease", "rescission"],
    "landlord": ["lessor", "property owner", "owner"],
    "tenant": ["lessee", "occupant"],
    "rent": ["lease payment", "rental"],

    # Company terms
    "start a company": ["incorporate", "form a company", "company formation",
                        "registration of company"],
    "business": ["company", "enterprise", "commercial activity", "trade"],
    "owner": ["shareholder", "member", "proprietor"],
    "boss": ["director", "manager", "employer"],

    # Criminal terms
    "steal": ["theft", "larceny", "stealing"],
    "robbery": ["theft with violence", "armed robbery"],
    "assault": ["bodily harm", "physical attack", "battery"],
    "murder": ["homicide", "wilful homicide", "killing"],

    # General legal terms
    "law": ["act", "statute", "legislation", "enactment"],
    "rule": ["regulation", "provision", "requirement"],
    "fine": ["penalty", "multa", "monetary penalty"],
    "jail": ["imprisonment", "prison", "detention", "incarceration"],
    "sue": ["bring action", "institute proceedings", "file suit", "litigation"],
    "court": ["tribunal", "judiciary"],
    "judge": ["magistrate", "adjudicator"],
    "lawyer": ["advocate", "attorney", "legal practitioner", "counsel"],

    # Maltese-specific
    "Cap.": ["Chapter", "CAP", "Cap"],
    "S.L.": ["SL", "Subsidiary Legislation"],
    "L.N.": ["LN", "Legal Notice"],
}


def expand_query(query: str, synonym_dict: dict = None) -> List[str]:
    """
    Expand a query with synonyms.

    Returns list of expanded terms to add to the search.
    """
    if synonym_dict is None:
        synonym_dict = MALTESE_LEGAL_SYNONYMS

    expanded_terms = []
    query_lower = query.lower()

    for term, synonyms in synonym_dict.items():
        if term.lower() in query_lower:
            expanded_terms.extend(synonyms)

    return list(set(expanded_terms))


def get_tests_by_failure_mode(mode: FailureMode) -> List[RAGTestQuestion]:
    """Get all test questions for a specific failure mode."""
    return [q for q in ALL_TEST_QUESTIONS if q.failure_mode == mode]


def get_tests_by_difficulty(difficulty: str) -> List[RAGTestQuestion]:
    """Get all test questions of a specific difficulty."""
    return [q for q in ALL_TEST_QUESTIONS if q.difficulty == difficulty]


# =============================================================================
# TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("RAG TEST QUESTIONS FOR MALTESE LAW SYSTEM")
    print("=" * 70)

    print(f"\nTotal test questions: {len(ALL_TEST_QUESTIONS)}")
    print("\nBy failure mode:")
    for mode in FailureMode:
        tests = get_tests_by_failure_mode(mode)
        print(f"  {mode.value}: {len(tests)} tests")

    print("\nBy difficulty:")
    for diff in ["easy", "medium", "hard"]:
        tests = get_tests_by_difficulty(diff)
        print(f"  {diff}: {len(tests)} tests")

    print("\n" + "=" * 70)
    print("SYNONYM MISMATCH TESTS (most relevant for orange/amber issue)")
    print("=" * 70)

    for test in SYNONYM_TESTS:
        print(f"\n[{test.id}] {test.query}")
        print(f"  Expected laws: {', '.join(test.expected_laws)}")
        print(f"  User terms: {', '.join(test.synonyms)}")
        print(f"  Legal terms: {', '.join(test.legal_terms)}")
        print(f"  Difficulty: {test.difficulty}")

    print("\n" + "=" * 70)
    print("QUERY EXPANSION EXAMPLE")
    print("=" * 70)

    sample_query = "What are the rules for orange traffic lights?"
    expanded = expand_query(sample_query)
    print(f"\nOriginal: {sample_query}")
    print(f"Expanded terms: {expanded}")
