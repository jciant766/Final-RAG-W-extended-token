# Maltese Law RAG System

A production-ready Retrieval Augmented Generation (RAG) system for querying 600+ chapters of Maltese legislation.

## Features

- **Voyage AI voyage-law-2**: Best-in-class legal embeddings (1024 dimensions, 16K context)
- **Hybrid Search**: BM25 + Vector search with Reciprocal Rank Fusion
- **Voyage rerank-2**: Neural reranking for ~14% accuracy improvement
- **Smart Query Routing**: LLM-powered query analysis and filtering
- **Legal Citations**: Proper [Chapter X, Article Y] citations in responses
- **Streamlit UI**: Clean interface for legal research

## Quick Start

### 1. Install Dependencies

```bash
cd maltese-law-rag
pip install -r requirements.txt
```

### 2. Set Up Environment

The `.env` file should contain:
```
VOYAGE_API_KEY=your_voyage_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

### 3. Add PDF Files

Place your Maltese law PDF files in `data/pdfs/`

### 4. Run Ingestion

```bash
python scripts/ingest_laws.py data/pdfs/
```

### 5. Test Retrieval

```bash
python scripts/test_retrieval.py
```

### 6. Launch UI

```bash
streamlit run app.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION                              │
├─────────────────────────────────────────────────────────────────────┤
│  PDF Files → PyMuPDF Extraction → Legal Parser → Hierarchical      │
│  Chunker → Voyage voyage-law-2 Embeddings → LanceDB                │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      RETRIEVAL PIPELINE                             │
├─────────────────────────────────────────────────────────────────────┤
│  User Query → LLM Router (Claude Haiku) → Extract Filters          │
│            → Hybrid Search (BM25 + Vector)                         │
│            → Voyage rerank-2 Reranker → Top Results                │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         GENERATION                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Top Chunks + Query → Claude Sonnet via OpenRouter →               │
│  Response with Citations [Chapter X, Article Y]                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
maltese-law-rag/
├── app.py                      # Streamlit application
├── requirements.txt            # Dependencies
├── .env                        # API keys (DO NOT COMMIT)
├── README.md
│
├── src/
│   ├── extraction/
│   │   └── pdf_extractor.py    # PyMuPDF text extraction
│   ├── parsing/
│   │   └── legal_parser.py     # Parse legal structure
│   ├── chunking/
│   │   └── legal_chunker.py    # Hierarchical chunking
│   ├── embeddings/
│   │   └── voyage_embeddings.py# Voyage AI voyage-law-2
│   ├── database/
│   │   └── vector_store.py     # LanceDB operations
│   ├── retrieval/
│   │   ├── hybrid_retriever.py # BM25 + Vector with RRF
│   │   ├── reranker.py         # Voyage rerank-2
│   │   └── query_router.py     # LLM-based routing
│   └── generation/
│       └── response_generator.py
│
├── scripts/
│   ├── ingest_laws.py          # Full ingestion pipeline
│   └── test_retrieval.py       # Test queries
│
├── data/
│   └── pdfs/                   # Place PDF files here
│
└── lancedb_data/               # Vector database (auto-created)
```

## Legal Parser Configuration

**⚠️ IMPORTANT**: The legal parser contains placeholder regex patterns that must be updated based on the actual structure of your PDF files.

After examining sample PDFs, update the patterns in `src/parsing/legal_parser.py` to match:
- Chapter formatting (e.g., "CHAPTER 386" vs "Cap. 386")
- Article numbering (e.g., "Article 5." vs "Art. 5")
- Sub-article structure (e.g., "(1)" vs "1.")
- Cross-reference formats

## Tech Stack

| Component | Technology |
|-----------|------------|
| Embedding Model | Voyage AI `voyage-law-2` |
| Reranker | Voyage AI `rerank-2` |
| Vector Database | LanceDB |
| Hybrid Search | BM25 + Vector with RRF |
| LLM (Generation) | Claude Sonnet via OpenRouter |
| LLM (Routing) | Claude Haiku via OpenRouter |
| PDF Extraction | PyMuPDF |
| UI | Streamlit |

## API Usage Notes

- **Voyage AI**: 50M free tokens for voyage-law-2
- **OpenRouter**: Pay per token - monitor usage
- **LanceDB**: Fully embedded, no external service needed

## License

MIT
