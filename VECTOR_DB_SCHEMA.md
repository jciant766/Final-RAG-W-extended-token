# Vector Database Schema for Maltese Law RAG

## Design Principles

Based on your requirements:
- **Fine-grained granularity**: Separate vectors for summaries, articles, schedules, forms
- **Graph RAG enabled**: Cross-reference edges for relationship traversal
- **No versioning**: Current version only
- **Metadata fields**: code, name, type, parent_code, categories, page numbers

---

## Collection 1: `law_summaries` (4,093 documents)

Each law gets ONE summary vector for initial filtering.

```json
{
  "id": "law_S.L.441.04",
  "type": "law_summary",

  // === TEXT TO EMBED ===
  "text": "These regulations govern activities requiring permits from Maltese Local Councils under the framework of the Trading Licences Act. Covers local council permits, fees, open-air markets, and market hawker licensing.",

  // === METADATA FOR FILTERING ===
  "metadata": {
    "code": "S.L. 441.04",
    "name": "Activities Requiring Permit by Local Councils Regulations",
    "law_type": "subsidiary",
    "parent_code": "Cap. 441",
    "categories": ["administrative_law", "commercial_law"],
    "total_articles": 45,
    "total_schedules": 12,
    "total_forms": 4,
    "has_forms": true,
    "has_tables": true
  },

  // === GRAPH EDGES (for traversal) ===
  "edges": {
    "parent": "law_Cap.441",
    "children": [],  // Only for parent laws
    "references_laws": ["Cap. 16", "Cap. 363"],  // External law references
    "referenced_by": []  // Populated during indexing
  }
}
```

---

## Collection 2: `articles` (~15,000-50,000 documents)

**OPTION A IMPLEMENTATION**: Each MAIN article becomes one vector containing all sub-articles combined.

```json
{
  "id": "art_S.L.441.04_5",
  "type": "article",

  // === TEXT TO EMBED (Combined with markers) ===
  "text": "Article 5 - Permits\n\n[5(1)] Any person who wishes to carry out an activity requiring a permit shall submit an application to the local council in the prescribed form together with the prescribed fee.\n\n[5(2)] The application shall be accompanied by:\n\n[5(2)(a)] proof of identity;\n\n[5(2)(b)] any supporting documentation.\n\n[5(3)] The local council shall process the application within 30 days.",

  // === METADATA FOR FILTERING ===
  "metadata": {
    "law_code": "S.L. 441.04",
    "law_name": "Activities Requiring Permit by Local Councils Regulations",
    "article_number": "5",
    "sub_articles": ["5", "5(1)", "5(2)", "5(2)(a)", "5(2)(b)", "5(3)"],
    "sub_articles_count": 6,
    "start_page": 2,
    "end_page": 3,
    "categories": ["administrative_law", "commercial_law"]
  },

  // === GRAPH EDGES ===
  "edges": {
    "law": "law_S.L.441.04",
    "references_internal": ["art_S.L.441.04_3", "art_S.L.441.04_7"],
    "references_external": [
      {
        "law": "Cap. 16",
        "article": "3(2)",
        "main_article": "3",
        "id": "art_Cap.16_3"
      }
    ]
  }
}
```

**Why This Works:**
- Sub-articles `[5(1)]`, `[5(2)]` are searchable within the combined text
- Graph edges normalized to main articles (e.g., `5(2)` → `5`)
- LLM can cite specific sub-articles using markers
- ~85% fewer vectors while preserving all information

---

## Collection 3: `schedules` (~50,000+ documents)

Each schedule section becomes a separate vector.

```json
{
  "id": "sched_S.L.441.04_Table:Fees",
  "type": "schedule",

  // === TEXT TO EMBED ===
  "text": "Schedule of Fees for Permits: Permit for 2 weeks: €10. Permit for 1 month: €20. Permit for 3 months: €45. Annual permit: €150. Late renewal penalty: €25.",

  // === METADATA FOR FILTERING ===
  "metadata": {
    "law_code": "S.L. 441.04",
    "law_name": "Activities Requiring Permit by Local Councils Regulations",
    "schedule_number": "Schedule:Table:Fees",
    "schedule_name": "SCHEDULE B",
    "content_type": "schedule_table",
    "title": "Table of Fees",
    "start_page": 16,
    "end_page": 17,
    "categories": ["administrative_law", "commercial_law"]
  },

  // === GRAPH EDGES ===
  "edges": {
    "law": "law_S.L.441.04",
    "referenced_in_articles": ["art_S.L.441.04_5(4)", "art_S.L.441.04_8(1)"]
  }
}
```

---

## Collection 4: `forms` (~10,000+ documents)

Each form becomes a separate vector (using AI-generated summary).

```json
{
  "id": "form_S.L.441.04_page20",
  "type": "form",

  // === TEXT TO EMBED (AI-generated summary, NOT blank form text) ===
  "text": "Application form for obtaining a market hawker licence from Local Councils. Used by individuals or businesses seeking to sell goods in open-air markets. Requires applicant details, type of goods, and market location preference.",

  // === METADATA FOR FILTERING ===
  "metadata": {
    "law_code": "S.L. 441.04",
    "law_name": "Activities Requiring Permit by Local Councils Regulations",
    "form_title": "Application for Market Hawker Licence",
    "purpose": "Apply for a licence to operate as a market hawker",
    "who_uses_it": "Individuals or businesses seeking to sell goods in open-air markets",
    "page_number": 20,
    "screenshot_path": "form_screenshots/S_L_441_04_page_20.png",
    "categories": ["administrative_law", "commercial_law"]
  },

  // === GRAPH EDGES ===
  "edges": {
    "law": "law_S.L.441.04",
    "related_articles": ["art_S.L.441.04_5(1)", "art_S.L.441.04_6"]
  },

  // === FORM-SPECIFIC FIELDS ===
  "key_fields": [
    "Applicant name and ID card number",
    "Address and contact details",
    "Type of goods to be sold",
    "Market location preference",
    "Previous licence history",
    "Declaration and signature"
  ]
}
```

---

## Graph Edges Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GRAPH STRUCTURE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   Cap. 441      │ (Parent Law)
                    │   Trading       │
                    │   Licences Act  │
                    └────────┬────────┘
                             │ parent_of
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ S.L. 441.01 │   │ S.L. 441.04 │   │ S.L. 441.05 │
    │             │   │ (Our law)   │   │             │
    └─────────────┘   └──────┬──────┘   └─────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Article 5│   │ Schedule │   │  Form    │
        │   (1)    │   │ Table:   │   │ Page 20  │
        └────┬─────┘   │ Fees     │   └──────────┘
             │         └──────────┘
    references_internal
             │
             ▼
        ┌──────────┐
        │ Article 3│
        │   (2)    │
        └──────────┘

Edge Types:
- parent_of / child_of (law hierarchy)
- contains (law → articles/schedules/forms)
- references_internal (article → article in same law)
- references_external (article → article in different law)
- related_to (form → relevant articles)
```

---

## PostgreSQL Schema (with pgvector)

```sql
-- Law summaries
CREATE TABLE law_summaries (
    id VARCHAR(50) PRIMARY KEY,           -- "law_S.L.441.04"
    code VARCHAR(20) NOT NULL,            -- "S.L. 441.04"
    name TEXT NOT NULL,
    law_type VARCHAR(20),                 -- "parent" | "subsidiary"
    parent_code VARCHAR(20),              -- "Cap. 441"
    categories TEXT[],                    -- ["administrative_law", "commercial_law"]
    summary_text TEXT NOT NULL,
    total_articles INT,
    total_schedules INT,
    total_forms INT,
    has_forms BOOLEAN,
    has_tables BOOLEAN,
    embedding VECTOR(1536)                -- OpenAI embedding
);

CREATE INDEX idx_law_categories ON law_summaries USING GIN(categories);
CREATE INDEX idx_law_type ON law_summaries(law_type);
CREATE INDEX idx_law_parent ON law_summaries(parent_code);
CREATE INDEX idx_law_embedding ON law_summaries USING ivfflat(embedding vector_cosine_ops);

-- Articles
CREATE TABLE articles (
    id VARCHAR(100) PRIMARY KEY,          -- "art_S.L.441.04_5(1)"
    law_code VARCHAR(20) NOT NULL,
    law_name TEXT,
    article_number VARCHAR(30) NOT NULL,  -- "5(1)"
    parent_article VARCHAR(30),           -- "5"
    is_subarticle BOOLEAN,
    nesting_level INT,
    text TEXT NOT NULL,
    start_page INT,
    end_page INT,
    categories TEXT[],
    embedding VECTOR(1536)
);

CREATE INDEX idx_art_law ON articles(law_code);
CREATE INDEX idx_art_categories ON articles USING GIN(categories);
CREATE INDEX idx_art_embedding ON articles USING ivfflat(embedding vector_cosine_ops);

-- Schedules
CREATE TABLE schedules (
    id VARCHAR(100) PRIMARY KEY,          -- "sched_S.L.441.04_Table:Fees"
    law_code VARCHAR(20) NOT NULL,
    law_name TEXT,
    schedule_number VARCHAR(50) NOT NULL,
    schedule_name VARCHAR(100),
    content_type VARCHAR(20),             -- "schedule_text" | "schedule_table"
    title TEXT,
    text TEXT NOT NULL,
    start_page INT,
    end_page INT,
    categories TEXT[],
    embedding VECTOR(1536)
);

CREATE INDEX idx_sched_law ON schedules(law_code);
CREATE INDEX idx_sched_type ON schedules(content_type);
CREATE INDEX idx_sched_embedding ON schedules USING ivfflat(embedding vector_cosine_ops);

-- Forms
CREATE TABLE forms (
    id VARCHAR(100) PRIMARY KEY,          -- "form_S.L.441.04_page20"
    law_code VARCHAR(20) NOT NULL,
    law_name TEXT,
    form_title TEXT,
    purpose TEXT,
    who_uses_it TEXT,
    key_fields TEXT[],
    summary_text TEXT NOT NULL,           -- AI-generated summary for embedding
    page_number INT,
    screenshot_path TEXT,
    categories TEXT[],
    embedding VECTOR(1536)
);

CREATE INDEX idx_form_law ON forms(law_code);
CREATE INDEX idx_form_embedding ON forms USING ivfflat(embedding vector_cosine_ops);

-- Graph edges (cross-references)
CREATE TABLE edges (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,      -- "art_S.L.441.04_5(1)"
    target_id VARCHAR(100) NOT NULL,      -- "art_S.L.441.04_3(2)"
    edge_type VARCHAR(30) NOT NULL,       -- "references_internal" | "references_external" | "parent_of"
    source_type VARCHAR(20),              -- "article" | "law" | "schedule" | "form"
    target_type VARCHAR(20)
);

CREATE INDEX idx_edge_source ON edges(source_id);
CREATE INDEX idx_edge_target ON edges(target_id);
CREATE INDEX idx_edge_type ON edges(edge_type);
```

---

## RAG Query with Graph Traversal

```python
def rag_query(question: str, categories: List[str] = None):
    # Step 1: Embed question
    query_embedding = embed(question)

    # Step 2: Filter by categories (if provided)
    if categories:
        law_filter = f"categories && ARRAY{categories}"
    else:
        law_filter = "TRUE"

    # Step 3: Find relevant law summaries
    relevant_laws = db.query(f"""
        SELECT id, code, name, summary_text,
               1 - (embedding <=> $1) AS similarity
        FROM law_summaries
        WHERE {law_filter}
        ORDER BY embedding <=> $1
        LIMIT 5
    """, query_embedding)

    # Step 4: Find relevant articles within those laws
    law_codes = [law.code for law in relevant_laws]
    relevant_articles = db.query("""
        SELECT id, law_code, article_number, text,
               1 - (embedding <=> $1) AS similarity
        FROM articles
        WHERE law_code = ANY($2)
        ORDER BY embedding <=> $1
        LIMIT 10
    """, query_embedding, law_codes)

    # Step 5: Graph traversal - find related content
    article_ids = [art.id for art in relevant_articles]
    related_content = db.query("""
        SELECT DISTINCT e.target_id, e.edge_type,
               COALESCE(a.text, s.text, f.summary_text) AS related_text
        FROM edges e
        LEFT JOIN articles a ON e.target_id = a.id
        LEFT JOIN schedules s ON e.target_id = s.id
        LEFT JOIN forms f ON e.target_id = f.id
        WHERE e.source_id = ANY($1)
          AND e.edge_type IN ('references_internal', 'references_external', 'related_to')
    """, article_ids)

    # Step 6: Find relevant forms (if question mentions forms/applications)
    if any(word in question.lower() for word in ['form', 'apply', 'application', 'how do i']):
        relevant_forms = db.query("""
            SELECT id, law_code, form_title, summary_text, screenshot_path
            FROM forms
            WHERE law_code = ANY($1)
            ORDER BY embedding <=> $2
            LIMIT 3
        """, law_codes, query_embedding)

    # Step 7: Build context for LLM
    context = {
        "laws": relevant_laws,
        "articles": relevant_articles,
        "related": related_content,
        "forms": relevant_forms
    }

    return generate_response(question, context)
```

---

## Expected Database Size

| Collection | Count | Avg Text Size | Estimated Vectors |
|------------|-------|---------------|-------------------|
| law_summaries | 4,093 | ~500 chars | 4,093 |
| articles | ~200,000 | ~300 chars | 200,000 |
| schedules | ~50,000 | ~400 chars | 50,000 |
| forms | ~10,000 | ~200 chars | 10,000 |
| **Total** | **~264,093** | | **~264,093 vectors** |

With 1536-dimensional vectors (OpenAI):
- Storage: ~264,093 × 1536 × 4 bytes = **~1.6 GB** for vectors alone
- Plus metadata: ~**2-3 GB total**

---

## Unique IDs Format

Consistent ID format for all documents:

```
Law summaries:  law_{code}           → law_S.L.441.04
Articles:       art_{code}_{number}  → art_S.L.441.04_5(1)(a)
Schedules:      sched_{code}_{num}   → sched_S.L.441.04_Table:Fees
Forms:          form_{code}_page{n}  → form_S.L.441.04_page20
```

This enables easy graph traversal and deduplication.
