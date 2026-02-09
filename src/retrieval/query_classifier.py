"""
Query Classifier for Maltese Law RAG.

Classifies user queries into legal categories BEFORE semantic search.
This is the first stage of the hierarchical retrieval pipeline:

1. Query → Classify into categories (this module - fast LLM call)
2. Filter laws BY CATEGORY (instant, no embeddings needed)
3. Semantic search within filtered laws
4. Search articles within those laws

Research basis:
- Category-first filtering proven to improve precision (arxiv:2510.21711)
- Coarse-to-fine cascading reduces search space efficiently
- Legal queries often have clear domain signals
"""

import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# All valid categories from the Maltese law extractions
VALID_CATEGORIES = [
    "administrative_law",
    "aviation_law",
    "civil_law",
    "commercial_law",
    "company_law",
    "constitutional_law",
    "consumer_protection_law",
    "criminal_law",
    "customs_law",
    "data_protection_and_privacy",
    "education_law",
    "electoral_law",
    "electronic_communications_law",
    "employment_law",
    "energy_law",
    "environmental_law",
    "eu_law",
    "family_law",
    "financial_services_law",
    "food_safety_law",
    "gaming_and_gambling_law",
    "health_law",
    "human_rights_law",
    "immigration_law",
    "intellectual_property_law",
    "international_law",
    "maritime_law",
    "media_and_broadcasting_law",
    "notarial_and_registration_law",
    "occupational_health_and_safety",
    "planning_and_development_law",
    "police_and_law_enforcement_law",
    "property_law",
    "social_security_law",
    "tax_law",
    "transport_law",
]

# Category descriptions for better classification
# =============================================================================
# LEGAL TERM SYNONYMS FOR QUERY EXPANSION
# =============================================================================
# Maltese law (based on Roman-Napoleonic tradition) uses specific legal terms
# that may not match common English phrases. This mapping bridges the gap.
#
# Problem this solves: "statute of limitations" in common English is called
# "prescription" in Maltese law. Without expansion, semantic search may fail
# to find relevant articles because the terminology doesn't match.
#
# Format: {common_term: [legal_term1, legal_term2, ...]}
# =============================================================================
LEGAL_TERM_SYNONYMS = {
    # Time-barring concepts
    "statute of limitations": ["prescription", "time-barred", "lapse of time", "barred by the lapse"],
    "time limit": ["prescription", "time-barred", "peremption"],
    "deadline": ["prescription", "time limit", "peremption"],
    "limitation period": ["prescription", "prescriptive period"],

    # Liability and damages
    "medical malpractice": ["medical negligence", "professional negligence", "medical liability", "damages arising from"],
    "malpractice": ["negligence", "professional negligence", "fault", "culpa"],
    "negligence": ["fault", "culpa", "want of proper care", "imprudence"],
    "damages": ["compensation", "indemnity", "reparation"],
    "liability": ["responsibility", "obligation", "duty"],
    "sue": ["bring action", "institute proceedings", "file suit"],

    # Contract concepts
    "breach of contract": ["non-performance", "failure to perform", "breach of obligation"],
    "void contract": ["null contract", "nullity", "void ab initio"],
    "termination": ["rescission", "resolution", "revocation"],

    # Property concepts
    "ownership": ["dominium", "proprietorship", "right of property"],
    "possession": ["detention", "holding"],
    "easement": ["servitude", "right of way"],
    "mortgage": ["hypothec", "hypothecary"],

    # Criminal concepts
    "crime": ["offence", "criminal act", "punishable act"],
    "punishment": ["penalty", "sentence", "sanction", "liable to"],
    "imprisonment": ["detention", "incarceration", "custodial sentence"],
    "bail": ["provisional liberty", "release on bail"],
    "theft": ["stealing", "furtu", "whosoever steals", "guilty of theft"],
    "murder": ["homicide", "wilful homicide", "causes death", "killing"],
    "assault": ["bodily harm", "wounds", "hurts", "violence against"],
    "robbery": ["steals by violence", "theft with violence"],
    "fraud": ["defrauds", "fraudulent", "false pretences", "cheating"],
    "sentence": ["liable to imprisonment", "punishment of", "fine of"],

    # Procedure concepts
    "lawsuit": ["action", "suit", "proceedings", "cause"],
    "appeal": ["appellate proceedings", "remedy"],
    "court": ["tribunal", "judicature"],
    "judgment": ["sentence", "decision", "decree"],

    # Family law concepts
    "divorce": ["dissolution of marriage", "separation"],
    "custody": ["care and custody", "parental authority", "access rights"],
    "alimony": ["maintenance", "support", "alimentary obligation"],
    "inheritance": ["succession", "estate", "hereditary"],

    # Corporate concepts
    "director": ["administrator", "officer of company"],
    "shareholder": ["member", "stockholder"],
    "bankruptcy": ["insolvency", "judicial liquidation", "winding up"],

    # =============================================================================
    # TRAFFIC AND TRANSPORT TERMS
    # =============================================================================
    # Critical for traffic law queries - Maltese law uses specific terminology
    # that differs from common speech. S.L. 65.11 is the key regulation.

    # Traffic light colors - Users say "orange/yellow", law says "amber"
    "orange light": ["amber light", "amber signal", "yellow light"],
    "orange traffic light": ["amber light", "amber signal", "amber traffic signal"],
    "yellow light": ["amber light", "amber signal"],

    # Driving offenses
    "drunk driving": ["driving under the influence", "DUI", "intoxicated driving",
                      "blood alcohol", "breath test", "exceeding alcohol limit"],
    "speeding": ["exceeding speed limit", "speed restriction", "speed limit violation"],
    "red light": ["traffic signal", "traffic light violation", "contravening red light"],
    "jaywalking": ["pedestrian violation", "crossing other than at pedestrian crossing"],
    "traffic ticket": ["contravention notice", "fixed penalty", "traffic fine"],
    "parking ticket": ["parking contravention", "parking fine", "illegal parking"],

    # Vehicle terms
    "car": ["motor vehicle", "vehicle", "motor car"],
    "truck": ["heavy goods vehicle", "commercial vehicle", "goods vehicle"],
    "motorcycle": ["motor cycle", "two-wheeled vehicle"],
    "driver's license": ["driving licence", "driving permit", "licence to drive"],
    "license plate": ["registration plate", "number plate", "vehicle registration"],

    # Road and traffic terms
    "crosswalk": ["pedestrian crossing", "zebra crossing"],
    "highway": ["arterial road", "trunk road", "main road"],
    "intersection": ["junction", "road junction", "crossroads"],
    "traffic rules": ["motor vehicle regulations", "traffic regulations", "road traffic"],

    # Employment - additional terms
    "fire": ["dismiss", "termination of employment", "dismissal"],
    "fired": ["dismissed", "terminated", "let go"],
    "quit": ["resign", "resignation", "voluntary termination"],
    "wages": ["remuneration", "salary", "pay", "compensation"],
    "minimum wage": ["national minimum wage", "basic wage"],

    # Housing/Property - additional terms
    "evict": ["ejectment", "repossession", "termination of lease", "rescission of lease"],
    "landlord": ["lessor", "property owner"],
    "tenant": ["lessee", "occupant"],
    "rent": ["lease payment", "rental", "lease"],
    "deposit": ["security deposit", "rental deposit", "caution money"],
}


CATEGORY_DESCRIPTIONS = {
    "administrative_law": "Government procedures, public administration, licensing, permits, regulations",
    "aviation_law": "Aircraft, airports, aviation safety, air transport",
    "civil_law": "Contracts, obligations, torts, civil procedure, civil remedies",
    "commercial_law": "Business transactions, commercial contracts, trade",
    "company_law": "Company formation, directors, shareholders, corporate governance",
    "constitutional_law": "Constitution, fundamental rights, government structure",
    "consumer_protection_law": "Consumer rights, product safety, unfair practices",
    "criminal_law": "Crimes, offences, penalties, criminal procedure, prosecution",
    "customs_law": "Import/export duties, customs procedures",
    "data_protection_and_privacy": "Personal data, GDPR, privacy rights",
    "education_law": "Schools, universities, education standards, qualifications",
    "electoral_law": "Elections, voting, political parties",
    "electronic_communications_law": "Telecommunications, internet, electronic services",
    "employment_law": "Employment contracts, workers rights, termination, wages",
    "energy_law": "Electricity, gas, renewable energy, utilities",
    "environmental_law": "Pollution, waste, environmental protection, conservation",
    "eu_law": "EU directives, EU regulations, EU compliance",
    "family_law": "Marriage, divorce, children, custody, inheritance",
    "financial_services_law": "Banking, insurance, investment, financial regulation",
    "food_safety_law": "Food standards, hygiene, food labeling",
    "gaming_and_gambling_law": "Casinos, betting, gaming licenses",
    "health_law": "Healthcare, medicines, medical professionals, public health",
    "human_rights_law": "Fundamental rights, discrimination, equality",
    "immigration_law": "Visas, residence permits, citizenship, asylum",
    "intellectual_property_law": "Patents, trademarks, copyright",
    "international_law": "Treaties, international agreements",
    "maritime_law": "Ships, shipping, ports, maritime safety",
    "media_and_broadcasting_law": "Television, radio, press, media regulation",
    "notarial_and_registration_law": "Notaries, public registers, deeds",
    "occupational_health_and_safety": "Workplace safety, health at work",
    "planning_and_development_law": "Urban planning, building permits, development",
    "police_and_law_enforcement_law": "Police powers, law enforcement, public order",
    "property_law": "Real estate, land, property rights, leases, real estate agents, estate agents, property sales, property licensing",
    "social_security_law": "Pensions, benefits, social welfare",
    "tax_law": "Income tax, VAT, tax compliance, tax penalties",
    "transport_law": "Roads, vehicles, traffic, public transport",
}


class QueryClassifier:
    """
    Classifies legal queries into categories using an LLM.

    This is a fast, cheap operation (~100ms, minimal tokens) that
    dramatically improves retrieval precision by pre-filtering.
    """

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize the classifier.

        Args:
            model: Claude model to use (haiku recommended for speed/cost)
        """
        self.client = Anthropic()
        self.model = model
        self.categories = VALID_CATEGORIES
        self.category_descriptions = CATEGORY_DESCRIPTIONS

    def classify(
        self,
        query: str,
        max_categories: int = 3,
        confidence_threshold: float = 0.3
    ) -> Dict[str, any]:
        """
        Classify a query into legal categories using HYBRID approach.

        Combines:
        1. LLM classification (semantic understanding)
        2. Keyword matching (catches explicit domain terms)

        This ensures we don't miss obvious matches like "real estate" -> property_law.

        Args:
            query: The user's legal question
            max_categories: Maximum number of categories to return
            confidence_threshold: Minimum confidence to include a category

        Returns:
            Dict with:
                - categories: List of relevant category names
                - confidence: Dict of category -> confidence score
                - reasoning: Brief explanation of classification
        """
        # First, get keyword matches (instant, catches explicit terms)
        keyword_result = self.classify_with_keywords(query, max_categories=2)
        keyword_cats = set(keyword_result.get("categories", []))
        keyword_confidence = keyword_result.get("confidence", {})

        # Build the prompt
        categories_list = "\n".join([
            f"- {cat}: {self.category_descriptions.get(cat, '')}"
            for cat in self.categories
        ])

        prompt = f"""Classify this legal query into the most relevant categories from Maltese law.

Query: "{query}"

Available categories:
{categories_list}

Instructions:
1. Identify which legal domains this query relates to
2. Return 1-{max_categories} most relevant categories
3. Assign confidence scores (0.0-1.0) to each
4. Only include categories with confidence >= {confidence_threshold}

Respond in JSON format:
{{
    "categories": ["category1", "category2"],
    "confidence": {{"category1": 0.9, "category2": 0.6}},
    "reasoning": "Brief explanation"
}}

Only return valid categories from the list above."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse the response
            response_text = response.content[0].text

            # Extract JSON from response
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())

            # Validate categories
            valid_cats = [c for c in result.get("categories", []) if c in self.categories]

            # Filter by confidence threshold
            confidence = result.get("confidence", {})
            filtered_cats = [
                c for c in valid_cats
                if confidence.get(c, 0) >= confidence_threshold
            ]

            # HYBRID: Merge with keyword categories
            # Add keyword matches that LLM might have missed
            final_cats = list(filtered_cats)
            final_confidence = {c: confidence.get(c, 0) for c in filtered_cats}

            for kw_cat in keyword_cats:
                if kw_cat not in final_cats:
                    final_cats.append(kw_cat)
                    # Give keyword matches a moderate confidence
                    final_confidence[kw_cat] = keyword_confidence.get(kw_cat, 0.5)

            return {
                "categories": final_cats[:max_categories + 1],  # Allow one extra for keyword match
                "confidence": final_confidence,
                "reasoning": result.get("reasoning", ""),
                "raw_response": result,
                "keyword_additions": list(keyword_cats - set(filtered_cats))
            }

        except Exception as e:
            logger.error(f"Query classification failed: {e}")
            # Fallback: return empty (will search all categories)
            return {
                "categories": [],
                "confidence": {},
                "reasoning": f"Classification failed: {e}",
                "error": str(e)
            }

    def classify_with_keywords(
        self,
        query: str,
        max_categories: int = 3
    ) -> Dict[str, any]:
        """
        Fast keyword-based classification (no LLM call).

        Use this for simple queries or as a fallback.
        Less accurate but instant.
        """
        query_lower = query.lower()

        # Keyword mappings
        keyword_map = {
            "criminal_law": ["crime", "criminal", "offence", "penalty", "prison", "murder", "theft", "assault", "sentence"],
            "tax_law": ["tax", "vat", "income tax", "duty", "fiscal", "revenue"],
            "company_law": ["company", "director", "shareholder", "incorporation", "corporate", "registered office"],
            "employment_law": ["employment", "employee", "worker", "wage", "dismissal", "termination", "labour", "fired", "fire"],
            "property_law": ["property", "land", "lease", "tenant", "landlord", "real estate", "ownership", "estate agent", "immovable", "conveyancing", "evict", "rent"],
            "family_law": ["marriage", "divorce", "custody", "child", "spouse", "alimony", "inheritance"],
            "immigration_law": ["visa", "residence", "citizenship", "asylum", "immigrant", "permit"],
            "environmental_law": ["environment", "pollution", "waste", "emission", "conservation"],
            "health_law": ["health", "medical", "hospital", "medicine", "doctor", "patient"],
            "financial_services_law": ["bank", "insurance", "investment", "financial", "credit"],
            "consumer_protection_law": ["consumer", "refund", "warranty", "product safety"],
            "data_protection_and_privacy": ["data", "privacy", "gdpr", "personal information"],
            "planning_and_development_law": ["planning", "building permit", "construction", "development"],
            "civil_law": ["contract", "damages", "liability", "negligence", "tort"],
            "constitutional_law": ["constitution", "fundamental right", "government"],
            # Transport law - critical for traffic questions
            "transport_law": ["traffic", "driving", "vehicle", "car", "road", "parking", "speeding",
                             "red light", "orange light", "amber light", "yellow light", "traffic light",
                             "drunk driving", "license", "licence", "pedestrian", "highway", "accident"],
        }

        matches = {}
        for category, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                matches[category] = score / len(keywords)

        # Sort by score and take top N
        sorted_cats = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        top_cats = sorted_cats[:max_categories]

        return {
            "categories": [c[0] for c in top_cats],
            "confidence": {c[0]: c[1] for c in top_cats},
            "reasoning": "Keyword-based classification",
            "method": "keywords"
        }

    def expand_query(self, query: str) -> Dict[str, any]:
        """
        Expand a query with legal term synonyms.

        This handles the terminology gap between common English and legal terminology.
        For example: "statute of limitations" → adds "prescription" to the query.

        Args:
            query: The user's legal question

        Returns:
            Dict with:
                - original_query: The original query
                - expanded_query: Query with legal terms appended
                - expansions: List of {term: str, synonyms: [str]} for matched terms
        """
        query_lower = query.lower()
        expansions = []
        additional_terms = []

        # Find all matching terms and their synonyms
        for common_term, legal_terms in LEGAL_TERM_SYNONYMS.items():
            if common_term in query_lower:
                expansions.append({
                    "term": common_term,
                    "synonyms": legal_terms
                })
                # Add the most important synonym (first one) to the query
                # Don't add ALL synonyms as that could dilute the embedding
                additional_terms.extend(legal_terms[:2])

        if expansions:
            # Build expanded query by appending key legal terms
            # This helps the embedding capture the legal terminology
            unique_terms = list(set(additional_terms))
            expanded_query = f"{query} ({', '.join(unique_terms)})"
            logger.info(f"Query expanded: '{query}' → added terms: {unique_terms}")
        else:
            expanded_query = query

        return {
            "original_query": query,
            "expanded_query": expanded_query,
            "expansions": expansions,
            "terms_added": additional_terms if expansions else []
        }


def expand_query(query: str) -> Dict[str, any]:
    """
    Standalone function to expand a query with legal term synonyms.
    Creates a classifier instance and calls expand_query().
    """
    classifier = QueryClassifier()
    return classifier.expand_query(query)


def get_classifier(use_llm: bool = True) -> QueryClassifier:
    """Get a query classifier instance."""
    return QueryClassifier()


# Quick test
if __name__ == "__main__":
    classifier = QueryClassifier()

    test_queries = [
        "What are the penalties for tax evasion in Malta?",
        "How do I register a company?",
        "What is the sentence for murder?",
        "Can my landlord evict me without notice?",
        "What are my rights if I get arrested?",
    ]

    print("=" * 60)
    print("Query Classifier Test")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = classifier.classify(query)
        print(f"Categories: {result['categories']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reasoning: {result['reasoning']}")
