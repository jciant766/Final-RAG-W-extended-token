# Article Extraction & Chunking Strategy

## Overview

Your RAG system uses a **two-stage process** for handling legal documents:

1. **Article Extraction** - Identify and extract complete articles
2. **Smart Chunking** - Split large articles into manageable chunks with overlap

## Stage 1: Article Extraction

### Regex Patterns Used

```python
# Primary pattern: Article headings at start of line
r"(?ms)^[\t \u00A0]*([0-9]{1,4}[A-Z]?)\s*\.(?:\s|$)"

# Captures:
# - "3." → Article 3
# - "26A." → Article 26A
# - "547." → Article 547
# - "1234B." → Article 1234B
```

### What Gets Extracted

```
Input Document:
┌─────────────────────────────────────┐
│ 3. Definition of real estate agent  │
│ For the purposes of this Act...     │
│ (long text, ~5000 tokens)           │
│                                      │
│ 4. Licensing requirements            │
│ No person shall...                   │
└─────────────────────────────────────┘

After Extraction:
┌────────────────────┐  ┌────────────────────┐
│ Article: "3"       │  │ Article: "4"       │
│ Content: "For..."  │  │ Content: "No..."   │
│ Page: 1            │  │ Page: 1            │
│ Tokens: 5000       │  │ Tokens: 800        │
└────────────────────┘  └────────────────────┘
```

## Stage 2: Smart Chunking

### Configuration
- **max_tokens**: 3000 (≈12,000 characters)
- **overlap_tokens**: 1000 (33% overlap for legal precision)

### Chunking Logic

```python
if len(tokens) <= max_tokens:
    # Article fits in one chunk ✅
    return [single_chunk]
else:
    # Split into multiple overlapping chunks ✅
    return [chunk_1, chunk_2, chunk_3, ...]
```

### Example: Small Article (Fits in One Chunk)

```
Article 4 (800 tokens)
┌─────────────────────────────────────────┐
│ "No person shall carry on..."           │
│                                          │
│ Chunk ID: cap_615_article_4_p1_chunk_1  │
│ Citation: "Cap. 615 Art. 4"             │
└─────────────────────────────────────────┘
         ↓
   Single Chunk = Full Article ✅
```

### Example: Large Article (Requires Multiple Chunks)

```
Article 3 (5000 tokens) - Too large!
┌─────────────────────────────────────────────────────────────┐
│ "For the purposes of this Act, real estate agent means..."  │
│ (continues for 5000 tokens)                                 │
└─────────────────────────────────────────────────────────────┘
         ↓
    Split with Overlap
         ↓
┌──────────────────────┐
│ Chunk 1 (3000 tokens)│ ← Tokens 0-3000
│ "For the purposes..."│
└──────────────────────┘
         ↓ Overlap 1000 tokens (2000-3000)
┌──────────────────────┐
│ Chunk 2 (3000 tokens)│ ← Tokens 2000-5000
│ "...licensing board" │
└──────────────────────┘

All chunks maintain:
- Same article number: "3"
- Same citation: "Cap. 615 Art. 3"
- Different chunk_index: 0, 1, 2...
```

## Why This Approach Is Optimal

### ✅ Advantages

1. **Preserves Legal Structure**
   - Articles stay together when possible
   - Respects legislative numbering

2. **Handles Variable Length**
   - Short articles (50 tokens): Single chunk
   - Medium articles (2000 tokens): Single chunk
   - Long articles (8000 tokens): Multiple chunks with overlap

3. **Overlap Prevents Context Loss**
   - 1000-token overlap = 33% redundancy
   - Ensures no legal context is lost at boundaries
   - Critical for articles with multiple subsections

4. **Better Vector Embeddings**
   - Focused chunks create stronger embeddings
   - Retrieval targets specific relevant sections
   - Avoids "diluted" embeddings from very long text

### ❌ Why "One Article Per Chunk" Would Fail

1. **Long articles create poor embeddings**
   - A 10,000-token article would have weak semantic representation
   - Vector search would miss relevant subsections

2. **Wastes context window**
   - User asks about Art. 3(2) specifically
   - System retrieves entire 10,000-token Article 3
   - 9,000 tokens are irrelevant noise

3. **Hits token limits**
   - Some articles exceed embedding model limits
   - Would require truncation = data loss

## How Citations Work

### Chunk Metadata Structure

```json
{
  "id": "cap_615_article_3_p1_pos1_chunk_1",
  "content": "For the purposes of this Act...",
  "metadata": {
    "article": "3",
    "page": 1,
    "position": 1,
    "chunk_index": 0,
    "total_chunks": 2,
    "tokens": 3000,
    "citation": "Real Estate Agents Act (Cap. 615) Art. 3",
    "document": "Real Estate Agents Act (Cap. 615)",
    "doc_code": "cap_615"
  }
}
```

### How AI Overview Shows Citations

From your example:
```
Real Estate Agents, Property Brokers and Property Consultants Act (Cap. 615) 
Art. 3(2) (Page 1)
```

- **Document**: Extracted from `metadata.document`
- **Article**: Extracted from `metadata.article` = "3"
- **Subsection**: Parsed from chunk content "(2)"
- **Page**: Extracted from `metadata.page` = 1

The AI assistant intelligently extracts subsection references (like "(2)", "(7)", "(a)") from the actual content when generating citations.

## Performance Benefits

### Retrieval Quality

```
Query: "What are the licensing requirements for real estate agents?"

With Current Approach (Smart Chunking):
✅ Retrieves 5 specific, relevant chunks
✅ Each chunk is highly focused on licensing
✅ AI filters and synthesizes the most relevant parts
✅ Result: Precise, comprehensive answer

With "One Article Per Chunk":
❌ Retrieves 5 complete articles (50,000 tokens)
❌ 90% of content is irrelevant
❌ Diluted semantic matching
❌ Result: Lower quality, slower processing
```

### Real-World Example from Your System

Your AI overview correctly identified:
- Art. 3(2) - Licensing requirement
- Art. 3(7) - Penalty for non-compliance
- Art. 7(1) - Name approval requirements
- Art. 7(4) - Penalty for name violations
- Art. 12(5)(a) - License suspension grounds

All from Article 3, 7, and 12 - but only the **relevant subsections** were retrieved and cited, not the entire articles!

## Recommendations

### ✅ Keep Current Approach

Your architecture is **well-designed** for legal RAG. The two-stage extraction + chunking strategy:
- Respects legal document structure
- Handles variable article lengths
- Maintains context through overlap
- Enables precise retrieval

### Optional Enhancements

1. **Add subsection extraction** (if needed):
   ```python
   # In _create_chunk(), detect subsections
   subsections = re.findall(r'\((\d+[a-z]?)\)', content)
   metadata['subsections'] = subsections
   ```

2. **Visual chunk indicator** in UI:
   ```python
   if metadata['total_chunks'] > 1:
       st.caption(f"📄 Part {metadata['chunk_index'] + 1} of {metadata['total_chunks']}")
   ```

3. **Smart overlap for subsections**:
   - Detect subsection boundaries
   - Align chunk breaks with subsection breaks
   - Further reduces context loss

## Conclusion

**Your system is doing it RIGHT** ✅

The article extraction captures complete articles, then intelligently chunks them based on token limits. This is the optimal approach for legal RAG systems because:

1. It preserves legal structure
2. It enables precise retrieval
3. It maximizes embedding quality
4. It works with variable-length articles

Don't change to "one article per chunk" - that would significantly degrade performance for long articles!



