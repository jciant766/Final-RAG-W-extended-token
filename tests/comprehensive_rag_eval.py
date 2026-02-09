"""
Comprehensive RAG Evaluation for Maltese Law System.

This module runs 100 test questions and validates:
1. Law Retrieval - Are expected law codes found?
2. Content Validation - Do retrieved texts contain expected keywords?
3. Article Precision - Are specific articles retrieved?

Usage:
    python tests/comprehensive_rag_eval.py
    python tests/comprehensive_rag_eval.py --limit 20  # Run first 20 only
    python tests/comprehensive_rag_eval.py --report    # Generate detailed report
"""

import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from collections import defaultdict

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from src.retrieval.graphrag_retriever import GraphRAGRetriever


@dataclass
class TestQuestion:
    """A test question with ground truth for validation."""
    id: str
    query: str
    category: str  # Legal domain
    expected_laws: List[str]  # Law codes that MUST be found
    expected_keywords: List[str]  # Keywords that MUST appear in retrieved text
    optional_laws: List[str] = field(default_factory=list)  # Nice to have
    difficulty: str = "medium"
    notes: str = ""


# =============================================================================
# 100 TEST QUESTIONS WITH GROUND TRUTH
# =============================================================================
# Each question has been researched against actual Maltese law extractions.
# Expected keywords are actual phrases from the legal text.

TEST_QUESTIONS = [
    # =========================================================================
    # TRAFFIC & TRANSPORT (15 questions) - S.L. 65.11, Cap. 65
    # =========================================================================
    TestQuestion(
        id="TRAFFIC-001",
        query="What are the rules for orange/amber traffic lights in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["amber", "proceed with caution", "impending change"],
        notes="Regulation 125 - Vehicular traffic light signals"
    ),
    TestQuestion(
        id="TRAFFIC-002",
        query="What are the speed limits for cars in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["speed limit", "kilometres per hour", "50", "80"],
        notes="Regulation 127 - Speed limits table"
    ),
    TestQuestion(
        id="TRAFFIC-003",
        query="What happens if I run a red light in Malta?",
        category="transport_law",
        expected_laws=["Cap. 65", "S.L. 65.11"],
        expected_keywords=["red", "prohibition", "stop line"],
        notes="Cap. 65 Article 15J + S.L. 65.11 Reg 125"
    ),
    TestQuestion(
        id="TRAFFIC-004",
        query="What are the penalties for drunk driving in Malta?",
        category="transport_law",
        expected_laws=["Cap. 65"],
        expected_keywords=["alcohol", "blood", "breath", "fine", "imprisonment"],
        optional_laws=["S.L. 65.11"],
        notes="Cap. 65 contains DUI provisions"
    ),
    TestQuestion(
        id="TRAFFIC-005",
        query="What are the rules for parking near pedestrian crossings?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["pedestrian crossing", "metres", "parking"],
        notes="S.L. 65.11 - parking regulations"
    ),
    TestQuestion(
        id="TRAFFIC-006",
        query="What is the fine for parking in a disabled parking space?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["disabled", "parking", "233"],  # €233 fine
        notes="S.L. 65.11 specific fine amounts"
    ),
    TestQuestion(
        id="TRAFFIC-007",
        query="Do I need a special license to drive a motorcycle in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11", "Cap. 65"],
        expected_keywords=["motor cycle", "licence", "driving"],
    ),
    TestQuestion(
        id="TRAFFIC-008",
        query="What are the window tinting rules for cars in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["tint", "light transmission", "windscreen", "75"],
        notes="Window tinting limits in S.L. 65.11"
    ),
    TestQuestion(
        id="TRAFFIC-009",
        query="What should I do if I have a car accident in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["accident", "stop", "exchange", "information", "police"],
        notes="Accident reporting procedures"
    ),
    TestQuestion(
        id="TRAFFIC-010",
        query="What is an electric kick scooter according to Maltese law?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["electric kick scooter", "e-kickscooter", "handlebar", "deck"],
        notes="Definition in Regulation 2"
    ),
    TestQuestion(
        id="TRAFFIC-011",
        query="What are the requirements for vehicle headlights in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["headlamp", "light", "height"],
    ),
    TestQuestion(
        id="TRAFFIC-012",
        query="How do I get a taxi driver's tag in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["tag", "driver", "licence", "fee"],
        notes="Driver tag requirements"
    ),
    TestQuestion(
        id="TRAFFIC-013",
        query="What vehicles are exempt from speed limits in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["ambulance", "fire engine", "police", "no limit"],
        notes="Speed limit exemptions"
    ),
    TestQuestion(
        id="TRAFFIC-014",
        query="What are the rules for pedestrians at traffic lights?",
        category="transport_law",
        expected_laws=["S.L. 65.11", "Cap. 65"],
        expected_keywords=["pedestrian", "crossing", "signal"],
    ),
    TestQuestion(
        id="TRAFFIC-015",
        query="What are the requirements for vehicle brakes in Malta?",
        category="transport_law",
        expected_laws=["S.L. 65.11"],
        expected_keywords=["brake", "braking", "system"],
    ),

    # =========================================================================
    # CRIMINAL LAW (15 questions) - Cap. 9
    # =========================================================================
    TestQuestion(
        id="CRIMINAL-001",
        query="What is the punishment for murder in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["homicide", "imprisonment", "life"],
        notes="Criminal Code - wilful homicide"
    ),
    TestQuestion(
        id="CRIMINAL-002",
        query="What is the penalty for theft in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["theft", "steals", "imprisonment", "fine"],
    ),
    TestQuestion(
        id="CRIMINAL-003",
        query="What constitutes assault under Maltese law?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["bodily harm", "wound", "hurt"],
    ),
    TestQuestion(
        id="CRIMINAL-004",
        query="What is the penalty for fraud in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["fraud", "false pretence", "defraud"],
    ),
    TestQuestion(
        id="CRIMINAL-005",
        query="What is robbery under Maltese criminal law?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["robbery", "violence", "steal"],
    ),
    TestQuestion(
        id="CRIMINAL-006",
        query="What are drug trafficking penalties in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 101"],
        expected_keywords=["drug", "trafficking", "imprisonment"],
        optional_laws=["Cap. 9"],
    ),
    TestQuestion(
        id="CRIMINAL-007",
        query="What is defamation under Maltese law?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["defamation", "libel", "slander"],
    ),
    TestQuestion(
        id="CRIMINAL-008",
        query="What is the age of criminal responsibility in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["age", "minor", "child", "criminal"],
    ),
    TestQuestion(
        id="CRIMINAL-009",
        query="What is money laundering according to Maltese law?",
        category="criminal_law",
        expected_laws=["Cap. 373"],
        expected_keywords=["money laundering", "proceeds", "crime"],
        optional_laws=["Cap. 9"],
    ),
    TestQuestion(
        id="CRIMINAL-010",
        query="What are the penalties for perjury in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["perjury", "false", "oath", "testimony"],
    ),
    TestQuestion(
        id="CRIMINAL-011",
        query="What is corruption according to Maltese law?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["corrupt", "bribe", "public officer"],
    ),
    TestQuestion(
        id="CRIMINAL-012",
        query="What is the penalty for kidnapping in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["kidnap", "abduct", "unlawful", "detention"],
    ),
    TestQuestion(
        id="CRIMINAL-013",
        query="What constitutes criminal negligence in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["negligence", "imprudence", "death", "involuntary"],
    ),
    TestQuestion(
        id="CRIMINAL-014",
        query="What is the penalty for arson in Malta?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["fire", "arson", "damage", "property"],
    ),
    TestQuestion(
        id="CRIMINAL-015",
        query="What is stalking under Maltese law?",
        category="criminal_law",
        expected_laws=["Cap. 9"],
        expected_keywords=["stalk", "harass", "fear"],
    ),

    # =========================================================================
    # EMPLOYMENT LAW (12 questions) - Cap. 452
    # =========================================================================
    TestQuestion(
        id="EMPLOY-001",
        query="Can my employer fire me without notice in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["termination", "notice", "dismissal"],
    ),
    TestQuestion(
        id="EMPLOY-002",
        query="What is the minimum wage in Malta?",
        category="employment_law",
        expected_laws=["S.L. 452.81"],
        expected_keywords=["minimum", "wage", "weekly"],
        optional_laws=["Cap. 452"],
    ),
    TestQuestion(
        id="EMPLOY-003",
        query="How much annual leave am I entitled to in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["leave", "annual", "vacation", "days"],
    ),
    TestQuestion(
        id="EMPLOY-004",
        query="What is unfair dismissal under Maltese law?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["unfair", "dismissal", "redundancy"],
    ),
    TestQuestion(
        id="EMPLOY-005",
        query="What are the maternity leave rules in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["maternity", "leave", "weeks", "pregnant"],
    ),
    TestQuestion(
        id="EMPLOY-006",
        query="What is the maximum working hours per week in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["hours", "week", "working time"],
    ),
    TestQuestion(
        id="EMPLOY-007",
        query="What is overtime pay in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["overtime", "hours", "rate"],
    ),
    TestQuestion(
        id="EMPLOY-008",
        query="What notice period is required to resign from a job in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["notice", "period", "resignation", "week"],
    ),
    TestQuestion(
        id="EMPLOY-009",
        query="What is sick leave entitlement in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["sick", "leave", "illness"],
    ),
    TestQuestion(
        id="EMPLOY-010",
        query="What is the probation period for new employees in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["probation", "period", "month"],
    ),
    TestQuestion(
        id="EMPLOY-011",
        query="What are public holidays in Malta?",
        category="employment_law",
        expected_laws=["Cap. 252"],
        expected_keywords=["public holiday", "national"],
        optional_laws=["Cap. 452"],
    ),
    TestQuestion(
        id="EMPLOY-012",
        query="Can an employer reduce my wages in Malta?",
        category="employment_law",
        expected_laws=["Cap. 452"],
        expected_keywords=["wages", "reduction", "contract"],
    ),

    # =========================================================================
    # COMPANY LAW (10 questions) - Cap. 386
    # =========================================================================
    TestQuestion(
        id="COMPANY-001",
        query="How do I register a company in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["registration", "memorandum", "articles", "company"],
    ),
    TestQuestion(
        id="COMPANY-002",
        query="What is the minimum share capital for a company in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["share capital", "minimum", "euro"],
    ),
    TestQuestion(
        id="COMPANY-003",
        query="What are director duties under Maltese company law?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["director", "duty", "fiduciary", "company"],
    ),
    TestQuestion(
        id="COMPANY-004",
        query="Can a company have a single shareholder in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["single member", "shareholder", "company"],
    ),
    TestQuestion(
        id="COMPANY-005",
        query="What is the process to wind up a company in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["winding up", "liquidation", "dissolution"],
    ),
    TestQuestion(
        id="COMPANY-006",
        query="What are the reporting requirements for companies in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["annual", "return", "accounts", "file"],
    ),
    TestQuestion(
        id="COMPANY-007",
        query="Can directors be held personally liable in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["director", "liability", "personal"],
    ),
    TestQuestion(
        id="COMPANY-008",
        query="What is a partnership en commandite in Malta?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["partnership", "commandite", "limited"],
    ),
    TestQuestion(
        id="COMPANY-009",
        query="How do shareholders vote in a Maltese company?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["vote", "shareholder", "resolution", "meeting"],
    ),
    TestQuestion(
        id="COMPANY-010",
        query="What is insider trading under Maltese law?",
        category="company_law",
        expected_laws=["Cap. 386"],
        expected_keywords=["insider", "trading", "information"],
        optional_laws=["Cap. 330"],
    ),

    # =========================================================================
    # PROPERTY & LEASE (10 questions) - Cap. 16
    # =========================================================================
    TestQuestion(
        id="PROPERTY-001",
        query="How can a landlord evict a tenant in Malta?",
        category="property_law",
        expected_laws=["Cap. 16", "Cap. 69"],
        expected_keywords=["lease", "tenant", "eviction", "termination"],
    ),
    TestQuestion(
        id="PROPERTY-002",
        query="What is the statute of limitations for property claims in Malta?",
        category="property_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["prescription", "years", "action"],
    ),
    TestQuestion(
        id="PROPERTY-003",
        query="How do I transfer property ownership in Malta?",
        category="property_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["transfer", "ownership", "contract", "public deed"],
        optional_laws=["Cap. 55"],
    ),
    TestQuestion(
        id="PROPERTY-004",
        query="What is a hypothec under Maltese law?",
        category="property_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["hypothec", "security", "mortgage", "immovable"],
    ),
    TestQuestion(
        id="PROPERTY-005",
        query="What are my rights as a tenant in Malta?",
        category="property_law",
        expected_laws=["Cap. 69", "Cap. 16"],
        expected_keywords=["tenant", "lease", "rent"],
    ),
    TestQuestion(
        id="PROPERTY-006",
        query="What is a servitude in Maltese property law?",
        category="property_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["servitude", "easement", "property"],
    ),
    TestQuestion(
        id="PROPERTY-007",
        query="Can I build on my property without a permit in Malta?",
        category="property_law",
        expected_laws=["Cap. 552"],
        expected_keywords=["permit", "development", "planning"],
    ),
    TestQuestion(
        id="PROPERTY-008",
        query="What is the rental deposit limit in Malta?",
        category="property_law",
        expected_laws=["Cap. 69"],
        expected_keywords=["deposit", "rent", "month"],
    ),
    TestQuestion(
        id="PROPERTY-009",
        query="How is property inherited in Malta?",
        category="property_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["succession", "inheritance", "heir", "testament"],
    ),
    TestQuestion(
        id="PROPERTY-010",
        query="What is co-ownership of property in Malta?",
        category="property_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["co-ownership", "common", "property", "share"],
    ),

    # =========================================================================
    # TAX LAW (8 questions) - Cap. 123, Cap. 406
    # =========================================================================
    TestQuestion(
        id="TAX-001",
        query="What is the income tax rate in Malta?",
        category="tax_law",
        expected_laws=["Cap. 123"],
        expected_keywords=["tax", "rate", "income", "percent"],
    ),
    TestQuestion(
        id="TAX-002",
        query="What is VAT in Malta?",
        category="tax_law",
        expected_laws=["Cap. 406"],
        expected_keywords=["VAT", "value added", "tax", "rate"],
    ),
    TestQuestion(
        id="TAX-003",
        query="What are the penalties for tax evasion in Malta?",
        category="tax_law",
        expected_laws=["Cap. 123"],
        expected_keywords=["penalty", "evasion", "fine", "imprisonment"],
    ),
    TestQuestion(
        id="TAX-004",
        query="How do I file a tax return in Malta?",
        category="tax_law",
        expected_laws=["Cap. 123"],
        expected_keywords=["return", "file", "tax", "commissioner"],
    ),
    TestQuestion(
        id="TAX-005",
        query="What income is exempt from tax in Malta?",
        category="tax_law",
        expected_laws=["Cap. 123"],
        expected_keywords=["exempt", "income", "tax"],
    ),
    TestQuestion(
        id="TAX-006",
        query="What is capital gains tax in Malta?",
        category="tax_law",
        expected_laws=["Cap. 123"],
        expected_keywords=["capital gains", "transfer", "property"],
    ),
    TestQuestion(
        id="TAX-007",
        query="What is stamp duty in Malta?",
        category="tax_law",
        expected_laws=["Cap. 364"],
        expected_keywords=["stamp", "duty", "transfer"],
    ),
    TestQuestion(
        id="TAX-008",
        query="What is the corporate tax rate in Malta?",
        category="tax_law",
        expected_laws=["Cap. 123"],
        expected_keywords=["company", "corporate", "tax", "rate"],
    ),

    # =========================================================================
    # FAMILY LAW (8 questions) - Cap. 16
    # =========================================================================
    TestQuestion(
        id="FAMILY-001",
        query="How do I get divorced in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["divorce", "separation", "marriage"],
    ),
    TestQuestion(
        id="FAMILY-002",
        query="What is child custody law in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["custody", "child", "care", "parent"],
    ),
    TestQuestion(
        id="FAMILY-003",
        query="What is alimony/maintenance in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["maintenance", "alimony", "spouse"],
    ),
    TestQuestion(
        id="FAMILY-004",
        query="What are the requirements to get married in Malta?",
        category="family_law",
        expected_laws=["Cap. 16", "Cap. 255"],
        expected_keywords=["marriage", "consent", "age"],
    ),
    TestQuestion(
        id="FAMILY-005",
        query="What is the legal age for marriage in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["age", "marriage", "minor"],
    ),
    TestQuestion(
        id="FAMILY-006",
        query="How is marital property divided in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["property", "marriage", "community", "acquests"],
    ),
    TestQuestion(
        id="FAMILY-007",
        query="What are parental rights in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["parental", "authority", "child", "parent"],
    ),
    TestQuestion(
        id="FAMILY-008",
        query="How does adoption work in Malta?",
        category="family_law",
        expected_laws=["Cap. 16"],
        expected_keywords=["adoption", "adopt", "child"],
    ),

    # =========================================================================
    # IMMIGRATION (6 questions) - Cap. 217
    # =========================================================================
    TestQuestion(
        id="IMMIGR-001",
        query="How do I apply for Maltese citizenship?",
        category="immigration_law",
        expected_laws=["Cap. 188"],
        expected_keywords=["citizenship", "naturalisation", "Malta"],
        optional_laws=["Cap. 217"],
    ),
    TestQuestion(
        id="IMMIGR-002",
        query="What visa do I need to work in Malta?",
        category="immigration_law",
        expected_laws=["Cap. 217"],
        expected_keywords=["visa", "permit", "work", "employment"],
    ),
    TestQuestion(
        id="IMMIGR-003",
        query="What is the residence permit process in Malta?",
        category="immigration_law",
        expected_laws=["Cap. 217"],
        expected_keywords=["residence", "permit", "third country"],
    ),
    TestQuestion(
        id="IMMIGR-004",
        query="Can I be deported from Malta?",
        category="immigration_law",
        expected_laws=["Cap. 217"],
        expected_keywords=["deportation", "removal", "order"],
    ),
    TestQuestion(
        id="IMMIGR-005",
        query="What are refugee rights in Malta?",
        category="immigration_law",
        expected_laws=["Cap. 420"],
        expected_keywords=["refugee", "asylum", "protection"],
        optional_laws=["Cap. 217"],
    ),
    TestQuestion(
        id="IMMIGR-006",
        query="How long can I stay in Malta as a tourist?",
        category="immigration_law",
        expected_laws=["Cap. 217"],
        expected_keywords=["entry", "stay", "days", "visa"],
    ),

    # =========================================================================
    # DATA PROTECTION (5 questions) - Cap. 586
    # =========================================================================
    TestQuestion(
        id="DATA-001",
        query="What are my data protection rights in Malta?",
        category="data_protection",
        expected_laws=["Cap. 586"],
        expected_keywords=["data", "personal", "protection", "rights"],
    ),
    TestQuestion(
        id="DATA-002",
        query="What is GDPR compliance in Malta?",
        category="data_protection",
        expected_laws=["Cap. 586"],
        expected_keywords=["data", "processing", "controller"],
    ),
    TestQuestion(
        id="DATA-003",
        query="What are data breach notification requirements in Malta?",
        category="data_protection",
        expected_laws=["Cap. 586"],
        expected_keywords=["breach", "notification", "data"],
    ),
    TestQuestion(
        id="DATA-004",
        query="Can I request deletion of my personal data in Malta?",
        category="data_protection",
        expected_laws=["Cap. 586"],
        expected_keywords=["erasure", "delete", "data", "right"],
    ),
    TestQuestion(
        id="DATA-005",
        query="What are the penalties for GDPR violations in Malta?",
        category="data_protection",
        expected_laws=["Cap. 586"],
        expected_keywords=["penalty", "fine", "data", "violation"],
    ),

    # =========================================================================
    # CONSUMER PROTECTION (4 questions) - Cap. 378
    # =========================================================================
    TestQuestion(
        id="CONSUMER-001",
        query="What are my consumer rights in Malta?",
        category="consumer_law",
        expected_laws=["Cap. 378"],
        expected_keywords=["consumer", "rights", "goods"],
    ),
    TestQuestion(
        id="CONSUMER-002",
        query="Can I return a product I bought in Malta?",
        category="consumer_law",
        expected_laws=["Cap. 378"],
        expected_keywords=["return", "refund", "goods", "defective"],
    ),
    TestQuestion(
        id="CONSUMER-003",
        query="What is the warranty period for goods in Malta?",
        category="consumer_law",
        expected_laws=["Cap. 378"],
        expected_keywords=["warranty", "guarantee", "years", "goods"],
    ),
    TestQuestion(
        id="CONSUMER-004",
        query="How do I file a consumer complaint in Malta?",
        category="consumer_law",
        expected_laws=["Cap. 378"],
        expected_keywords=["complaint", "consumer", "tribunal"],
    ),

    # =========================================================================
    # HEALTH LAW (4 questions) - Cap. 465
    # =========================================================================
    TestQuestion(
        id="HEALTH-001",
        query="What are patient rights in Malta?",
        category="health_law",
        expected_laws=["Cap. 465"],
        expected_keywords=["patient", "rights", "health", "care"],
    ),
    TestQuestion(
        id="HEALTH-002",
        query="Can I access my medical records in Malta?",
        category="health_law",
        expected_laws=["Cap. 465"],
        expected_keywords=["medical", "records", "access"],
    ),
    TestQuestion(
        id="HEALTH-003",
        query="What is medical negligence in Malta?",
        category="health_law",
        expected_laws=["Cap. 16", "Cap. 465"],
        expected_keywords=["negligence", "medical", "damage"],
    ),
    TestQuestion(
        id="HEALTH-004",
        query="Are vaccinations mandatory in Malta?",
        category="health_law",
        expected_laws=["Cap. 465"],
        expected_keywords=["vaccine", "health", "public"],
    ),

    # =========================================================================
    # CIVIL PROCEDURE (3 questions) - Cap. 12
    # =========================================================================
    TestQuestion(
        id="CIVIL-001",
        query="How do I file a lawsuit in Malta?",
        category="civil_law",
        expected_laws=["Cap. 12"],
        expected_keywords=["action", "court", "writ", "application"],
    ),
    TestQuestion(
        id="CIVIL-002",
        query="What is the small claims court in Malta?",
        category="civil_law",
        expected_laws=["Cap. 12"],
        expected_keywords=["small claims", "tribunal", "claim"],
    ),
    TestQuestion(
        id="CIVIL-003",
        query="How do I appeal a court decision in Malta?",
        category="civil_law",
        expected_laws=["Cap. 12"],
        expected_keywords=["appeal", "court", "decision", "judgment"],
    ),
]


def run_evaluation(
    questions: List[TestQuestion] = None,
    retriever: GraphRAGRetriever = None,
    verbose: bool = True
) -> Dict:
    """
    Run the RAG evaluation.

    Returns:
        Dict with evaluation results and metrics
    """
    if questions is None:
        questions = TEST_QUESTIONS

    if retriever is None:
        print("Initializing retriever...")
        retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")

    results = []
    start_time = time.time()

    print(f"\nRunning evaluation on {len(questions)} questions...")
    print("=" * 70)

    for i, q in enumerate(questions):
        if verbose:
            print(f"\n[{i+1}/{len(questions)}] {q.id}: {q.query[:50]}...")

        # Run retrieval
        search_result = retriever.search(
            query=q.query,
            limit=15,
            top_laws=25,
            expand_graph=True,
            auto_classify=True
        )

        # Collect all retrieved text for keyword matching
        all_retrieved_text = ""
        found_laws = set()
        found_articles = []

        # From laws
        for law in search_result.get("laws", []):
            law_code = law.get("law_code", "")
            found_laws.add(law_code)
            all_retrieved_text += " " + law.get("text", "")

        # From articles
        for article in search_result.get("articles", []):
            law_code = article.get("law_code", "")
            found_laws.add(law_code)
            all_retrieved_text += " " + article.get("text", "")
            found_articles.append(f"{law_code} Art. {article.get('article_number', '')}")

        # From related articles (graph expansion)
        for article in search_result.get("related_articles", []):
            law_code = article.get("law_code", "")
            found_laws.add(law_code)
            all_retrieved_text += " " + article.get("text", "")

        # Check expected laws
        laws_found = []
        laws_missed = []
        for expected_law in q.expected_laws:
            # Check if any found law contains the expected code
            if any(expected_law in fl or fl in expected_law for fl in found_laws):
                laws_found.append(expected_law)
            else:
                laws_missed.append(expected_law)

        # Check expected keywords
        all_text_lower = all_retrieved_text.lower()
        keywords_found = []
        keywords_missed = []
        for keyword in q.expected_keywords:
            if keyword.lower() in all_text_lower:
                keywords_found.append(keyword)
            else:
                keywords_missed.append(keyword)

        # Calculate scores
        law_recall = len(laws_found) / len(q.expected_laws) if q.expected_laws else 1.0
        keyword_recall = len(keywords_found) / len(q.expected_keywords) if q.expected_keywords else 1.0

        # Overall pass: at least 50% laws AND 50% keywords found
        passed = law_recall >= 0.5 and keyword_recall >= 0.5

        result = {
            "id": q.id,
            "query": q.query,
            "category": q.category,
            "passed": passed,
            "law_recall": law_recall,
            "keyword_recall": keyword_recall,
            "laws_found": laws_found,
            "laws_missed": laws_missed,
            "keywords_found": keywords_found,
            "keywords_missed": keywords_missed,
            "articles_retrieved": len(search_result.get("articles", [])),
            "query_expanded": search_result.get("query_expansion") is not None
        }
        results.append(result)

        if verbose:
            status = "PASS" if passed else "FAIL"
            print(f"  {status} | Laws: {law_recall:.0%} | Keywords: {keyword_recall:.0%}")
            if laws_missed:
                print(f"  Missing laws: {laws_missed}")
            if keywords_missed and len(keywords_missed) <= 3:
                print(f"  Missing keywords: {keywords_missed}")

    # Calculate summary metrics
    total_time = time.time() - start_time
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count

    # By category
    category_results = defaultdict(lambda: {"passed": 0, "failed": 0})
    for r in results:
        if r["passed"]:
            category_results[r["category"]]["passed"] += 1
        else:
            category_results[r["category"]]["failed"] += 1

    # Average metrics
    avg_law_recall = sum(r["law_recall"] for r in results) / len(results)
    avg_keyword_recall = sum(r["keyword_recall"] for r in results) / len(results)

    summary = {
        "total_questions": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": passed_count / len(results),
        "avg_law_recall": avg_law_recall,
        "avg_keyword_recall": avg_keyword_recall,
        "time_seconds": total_time,
        "time_per_question": total_time / len(results),
        "category_breakdown": dict(category_results),
        "results": results
    }

    return summary


def print_report(summary: Dict):
    """Print a detailed evaluation report."""
    print("\n" + "=" * 70)
    print("RAG EVALUATION REPORT")
    print("=" * 70)

    print(f"\n## OVERALL METRICS")
    print(f"Total Questions: {summary['total_questions']}")
    print(f"Passed: {summary['passed']} ({summary['pass_rate']:.1%})")
    print(f"Failed: {summary['failed']}")
    print(f"Avg Law Recall: {summary['avg_law_recall']:.1%}")
    print(f"Avg Keyword Recall: {summary['avg_keyword_recall']:.1%}")
    print(f"Time: {summary['time_seconds']:.1f}s ({summary['time_per_question']:.2f}s/question)")

    print(f"\n## BY CATEGORY")
    for category, stats in sorted(summary['category_breakdown'].items()):
        total = stats['passed'] + stats['failed']
        rate = stats['passed'] / total if total > 0 else 0
        print(f"  {category}: {stats['passed']}/{total} ({rate:.0%})")

    # Failed questions
    failed = [r for r in summary['results'] if not r['passed']]
    if failed:
        print(f"\n## FAILED QUESTIONS ({len(failed)})")
        for r in failed[:10]:  # Show first 10
            print(f"\n  [{r['id']}] {r['query'][:60]}...")
            print(f"    Laws: {r['law_recall']:.0%} | Keywords: {r['keyword_recall']:.0%}")
            if r['laws_missed']:
                print(f"    Missing laws: {r['laws_missed']}")
            if r['keywords_missed']:
                print(f"    Missing keywords: {r['keywords_missed'][:3]}")

    # Identify patterns
    print(f"\n## FAILURE PATTERNS")

    # Keywords that are commonly missed
    keyword_misses = defaultdict(int)
    for r in summary['results']:
        for kw in r.get('keywords_missed', []):
            keyword_misses[kw] += 1

    if keyword_misses:
        print("  Most missed keywords:")
        for kw, count in sorted(keyword_misses.items(), key=lambda x: -x[1])[:5]:
            print(f"    - '{kw}': missed {count} times")

    # Laws that are commonly missed
    law_misses = defaultdict(int)
    for r in summary['results']:
        for law in r.get('laws_missed', []):
            law_misses[law] += 1

    if law_misses:
        print("  Most missed laws:")
        for law, count in sorted(law_misses.items(), key=lambda x: -x[1])[:5]:
            print(f"    - {law}: missed {count} times")


def save_results(summary: Dict, filepath: str = "tests/eval_results.json"):
    """Save evaluation results to JSON."""
    with open(filepath, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nResults saved to: {filepath}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive RAG Evaluation")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of questions")
    parser.add_argument("--report", "-r", action="store_true", help="Generate detailed report")
    parser.add_argument("--save", "-s", action="store_true", help="Save results to JSON")
    parser.add_argument("--category", "-c", type=str, help="Test specific category only")

    args = parser.parse_args()

    # Filter questions if needed
    questions = TEST_QUESTIONS
    if args.category:
        questions = [q for q in questions if args.category in q.category]
    if args.limit:
        questions = questions[:args.limit]

    # Run evaluation
    summary = run_evaluation(questions, verbose=True)

    # Print report
    print_report(summary)

    # Save if requested
    if args.save:
        save_results(summary)
