# Graph RAG Format - Malta Laws Knowledge Graph

## Overview

The Malta Laws extraction system now outputs data in proper **Graph RAG format** following international standards (Akoma Ntoso, LegalDocML).

## Node Types and ID Format

### 1. Law Nodes
```
ID Format: law:Cap.16
Type: law_summary
```

**Example:**
```json
{
  "id": "law:Cap.16",
  "type": "law_summary",
  "text": "The Civil Code consolidates and amends the civil laws of Malta...",
  "metadata": {
    "code": "Cap. 16",
    "name": "Civil Code",
    "law_type": "parent",
    "parent_code": null,
    "categories": ["civil_law", "contracts"],
    "total_articles": 2257
  },
  "edges": {
    "parent": null,
    "children": [],
    "references_laws": ["Cap.490", "Cap.386"]
  }
}
```

### 2. Article Nodes
```
ID Format: art:Cap.16/art/1A
Type: article
```

**Example:**
```json
{
  "id": "art:Cap.16/art/28A",
  "type": "article",
  "text": "Article 28A. [full text including sub-articles]",
  "metadata": {
    "law_code": "Cap. 16",
    "law_name": "Civil Code",
    "article_number": "28A",
    "sub_articles": ["28A", "28A(1)", "28A(2)"],
    "sub_articles_count": 3,
    "start_page": 45,
    "end_page": 46,
    "categories": ["civil_law"],
    
    // Graph RAG properties
    "nesting_level": 0,           // 0=main, 1=sub, 2=para
    "has_sub_articles": true,     // Has children
    "is_sub_article": true        // Has letter suffix
  },
  "edges": {
    "law": "law:Cap.16",
    "references_internal": ["art:Cap.16/art/3", "art:Cap.16/art/7"],
    "references_external": []
  }
}
```

### 3. Schedule Nodes (if present)
```
ID Format: sched:S.L.441.07/sched/First
Type: schedule
```

## Edge Types (Graph RAG Standard)

### 1. INTERNAL_REF
Article → Article (same law)

```json
{
  "source_id": "art:Cap.16/art/1A",
  "target_id": "art:Cap.16/art/3",
  "type": "INTERNAL_REF",
  "properties": {
    "edge_type": "internal",
    "confidence": 1.0,
    "extraction_method": "gemini_vision",
    "citation_type": "article"
  },
  "source_type": "article",
  "target_type": "article"
}
```

### 2. EXTERNAL_REF
Article → Law (whole law reference, no specific article)

```json
{
  "source_id": "art:Cap.386/art/12",
  "target_id": "law:Cap.16",
  "type": "EXTERNAL_REF",
  "properties": {
    "edge_type": "external",
    "confidence": 1.0,
    "extraction_method": "gemini_vision",
    "citation_type": "law",
    "context": "References Civil Code"
  },
  "source_type": "article",
  "target_type": "law"
}
```

### 3. CITES
Article → Article (different law, specific article)

```json
{
  "source_id": "art:Cap.386/art/12",
  "target_id": "art:Cap.16/art/1085",
  "type": "CITES",
  "properties": {
    "edge_type": "external",
    "confidence": 1.0,
    "extraction_method": "gemini_vision",
    "citation_type": "article",
    "context": "References art. 1085 of Civil Code"
  },
  "source_type": "article",
  "target_type": "article"
}
```

## Nesting Levels

| Article Number | Nesting Level | Is Sub-article? |
|---------------|---------------|-----------------|
| `1`           | 0             | No              |
| `1A`          | 0             | Yes             |
| `1(1)`        | 1             | Yes             |
| `1(1)(a)`     | 2             | Yes             |
| `28G`         | 0             | Yes             |
| `28G(2)`      | 1             | Yes             |

## Edge Properties (Required)

All edges must include:
- `edge_type`: "internal" or "external"
- `confidence`: 0.0-1.0 (1.0 for direct references, 0.8 for unresolved)
- `extraction_method`: "gemini_vision"
- `citation_type`: "article", "law", "schedule"
- `context`: Human-readable description (optional)

## Vector Database Integration

Each article becomes a separate document for vector search:
- **ID**: Graph RAG URI format (`art:Cap.16/art/1A`)
- **Text**: Combined main article + all sub-articles
- **Metadata**: Rich properties for filtering
- **Edges**: Pre-computed for graph traversal

## Graph Traversal Examples

### 1. Find all articles referenced by Article 1A
```cypher
MATCH (a:Article {id: "art:Cap.16/art/1A"})-[r:INTERNAL_REF]->(target)
RETURN target
```

### 2. Find all external law references from Cap. 16
```cypher
MATCH (a:Article)-[r:EXTERNAL_REF|CITES]->(target)
WHERE a.id STARTS WITH "art:Cap.16/"
RETURN DISTINCT target
```

### 3. Find multi-hop references (Article 1A → Article 3 → Article 7)
```cypher
MATCH path = (a:Article {id: "art:Cap.16/art/1A"})-[:INTERNAL_REF*1..2]->(target)
RETURN path
```

## Advantages of Graph RAG Format

1. **URI-based IDs** - Globally unique, hierarchical
2. **Standardized edge types** - INTERNAL_REF, EXTERNAL_REF, CITES
3. **Rich metadata** - nesting_level, categories, temporal data
4. **Graph traversal** - Multi-hop queries for legal reasoning
5. **Hybrid retrieval** - Vector search + graph expansion
6. **Akoma Ntoso compatible** - International legal document standard

## Validation Checklist

✅ Law IDs use `law:Cap.X` format
✅ Article IDs use `art:Cap.X/art/Y` format  
✅ Schedule IDs use `sched:Cap.X/sched/Name` format
✅ All articles have `nesting_level` property
✅ All articles have `has_sub_articles` boolean
✅ All articles have `is_sub_article` boolean
✅ All edges use Graph RAG types (INTERNAL_REF, EXTERNAL_REF, CITES)
✅ All edges have properties (edge_type, confidence, extraction_method, citation_type)
✅ No UNKNOWN_ARTICLE_CONTINUATION entries in final output
✅ References are normalized to main article numbers

## File Outputs

- `vector_db_gemini_2_5_flash_vertex.json` - Graph RAG formatted output
- `article_extraction_gemini_2_5_flash_vertex.json` - Raw extraction with all details
- `debug_extraction_gemini_2_5_flash_vertex.json` - Debug information

---

**Ready for production deployment with 4,093 Malta laws!**
