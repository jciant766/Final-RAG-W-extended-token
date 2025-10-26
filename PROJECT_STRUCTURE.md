# 📁 Malta Legal RAG System - Project Structure

## 🎯 CORE SYSTEM OVERVIEW

This is a **Retrieval-Augmented Generation (RAG)** system for searching Malta commercial law documents. It combines:
- **Semantic search** using OpenAI embeddings
- **Vector database** (ChromaDB) for fast retrieval
- **AI-powered summaries** using GPT-4o-mini
- **Beautiful Streamlit interface** for end users

---

## 🏗️ ARCHITECTURE FLOW

```
PDFs → OCR Conversion → Text Files → Document Processor → Chunks → 
Vector Embeddings → ChromaDB → Search Engine → AI Assistant → Streamlit UI
```

---

## 📂 CLEAN FILE STRUCTURE (Post-Cleanup)

### **🔴 CORE APPLICATION FILES (DO NOT DELETE)**

#### Main Application
- `main.py` - **Streamlit web interface** (your main entry point)
- `env` - Environment variables (contains `OPENAI_API_KEY`)

#### Core Processing Pipeline
- `doc_processor.py` - **Document processor**: extracts articles, creates chunks
- `vector_store.py` - **Vector database interface**: ChromaDB + OpenAI embeddings
- `search_engine.py` - **Smart search engine**: query understanding + semantic search
- `ai_assistant.py` - **AI assistant**: generates overviews from retrieved articles
- `debug_logger.py` - **Logging system**: tracks queries and errors

#### Data Files
- `processed_chunks.json` - **Processed chunks** ready for vector DB
- `processing_report.json` - **Processing statistics**
- `malta_commercial_code_text.txt` - **Commercial Code (Cap. 13)** source text

#### Configuration
- `Requirements.txt` - Python dependencies (note: capital R)
- `README.md` - Project documentation

---

### **🟡 DATA DIRECTORIES**

#### ChromaDB Vector Database
```
chroma_db/
  └── chroma.sqlite3  # Your vector embeddings (DO NOT DELETE)
```

#### OCR Processing
```
ocr/
  ├── docling_ocr.py         # OCR conversion script (active)
  ├── requirements.txt       # OCR-specific dependencies
  ├── README.md             # OCR documentation
  ├── input_pdfs/           # ⚠️ SOURCE PDFs (21 files)
  │   └── SUBSIDIARY LEGISLATION 386 *.pdf
  └── output/               # 🟢 CONVERTED TEXT FILES (22 files)
      ├── Companies Act.txt
      └── SUBSIDIARY LEGISLATION *.txt
```

#### Debug Logs
```
debug_logs/
  ├── ai_assistant.log
  ├── doc_processor.log
  ├── main_app.log
  ├── queries.log
  ├── search_engine.log
  └── vector_store.log
```

---

### **⚠️ UNPROCESSED DATA**

#### Legislation Folder (43 PDFs)
```
Legislation/
  └── *.pdf  # 43 PDF files NOT currently being processed
```

**⚠️ IMPORTANT**: These 43 PDFs in the `Legislation/` folder are **NOT** being used by your system. 
- If you want them indexed, move them to `ocr/input_pdfs/` and run OCR conversion
- If they're duplicates or unnecessary, you can delete this folder

---

## 🔄 HOW TO USE THE SYSTEM

### **1. Run the Streamlit App**
```bash
streamlit run main.py
```

### **2. Add New Documents**
To add new legal documents to your RAG system:

1. Place PDF files in `ocr/input_pdfs/`
2. Run OCR conversion:
   ```bash
   cd ocr
   python docling_ocr.py
   ```
3. The system will:
   - Convert PDFs → text files in `ocr/output/`
   - Auto-process on next Streamlit startup
   - Extract articles/regulations
   - Chunk them (3000 tokens with 200 overlap)
   - Generate embeddings
   - Store in ChromaDB

### **3. Query the System**
- Open browser to `http://localhost:8501`
- Enter queries like:
  - "What is a trader?"
  - "Article 477"
  - "company director duties"
  - "bankruptcy procedures"

---

## 🗂️ WHAT WAS DELETED (Cleanup Summary)

### Folders Removed:
- ❌ `deprecated/` - Old preview/test scripts
- ❌ `test_chunking/` - Chunking quality tests
- ❌ `dashboards/` - Monitoring demos (not part of core RAG)
- ❌ `scripts/` - One-off utility scripts (batch converters, fixers, loaders)
- ❌ `ocr/test_output/` - Test files
- ❌ `ocr/demo_output/` - Demo files
- ❌ `__pycache__/` - Python cache files

### Files Removed:
- ❌ `document_processor.py` - Redundant wrapper
- ❌ `full_workflow.py` - Alternative workflow (not used)
- ❌ `all_processed_chunks.json` - Duplicate chunks file
- ❌ `chunks_dump.txt` - Old chunks dump
- ❌ `whole_article_chunking_demo.json` - Demo file
- ❌ `extracted_statutory_data_sample.json` - Sample extraction
- ❌ `load_chunks_to_db.py` - One-off loader script
- ❌ `reset_and_reprocess.py` - One-off utility
- ❌ `generate_questions.py` - Question generator
- ❌ `statutory_extractor.py` - Unused extractor
- ❌ `commercial_code_sample_questions.md` - Sample questions
- ❌ `DEPLOYMENT_GUIDE.md` - Outdated deployment guide
- ❌ `gcv_service_account.json` - Google Cloud credentials (not used)
- ❌ `ocr/file_bot.py` - Alternative OCR (not used)
- ❌ `ocr/gcv_ocr.py` - Google Cloud Vision OCR (not used)

---

## 🔧 SYSTEM CONFIGURATION

### Required Environment Variables (in `env` file):
```
OPENAI_API_KEY=your_key_here
```

### Key Parameters (in `doc_processor.py`):
- **Chunk size**: 3000 tokens
- **Overlap**: 200 tokens
- **Embedding model**: `text-embedding-3-large` (OpenAI)
- **AI model**: `gpt-4o-mini` (for overviews)

### ChromaDB Collection:
- **Name**: `malta_code_v2`
- **Distance metric**: Cosine similarity

---

## 📊 CURRENT DATA SOURCES

Your system currently processes:
1. ✅ **Commercial Code (Cap. 13)** - `malta_commercial_code_text.txt`
2. ✅ **Companies Act (Cap. 386)** - `ocr/output/Companies Act.txt`
3. ✅ **Subsidiary Legislation 386.02-386.24** - 20 text files in `ocr/output/`
4. ✅ **Subsidiary Legislation 595.27** - 1 text file

**Total**: 22 legal documents indexed

---

## 🚀 NEXT STEPS

### Option 1: Keep Legislation Folder
If those 43 PDFs in `Legislation/` are important:
1. Move them to `ocr/input_pdfs/`
2. Run OCR conversion
3. Restart the system to auto-process

### Option 2: Delete Legislation Folder
If they're duplicates or unnecessary:
```bash
Remove-Item -Recurse -Force Legislation
```

### Recommended: Add .gitignore
Create a `.gitignore` file:
```
__pycache__/
*.pyc
chroma_db/
debug_logs/
.env
env
gcv_service_account.json
processed_chunks.json
processing_report.json
```

---

## 📝 MAINTENANCE

### Clear Database and Reprocess
If you need to rebuild the vector database:
1. Delete `chroma_db/` folder
2. Delete `processed_chunks.json`
3. Restart Streamlit - it will auto-rebuild

### View Logs
Check `debug_logs/` for troubleshooting:
- `queries.log` - User search queries
- `ai_assistant.log` - AI overview generation
- `search_engine.log` - Search results

---

## 💡 TIPS

1. **Debug Mode**: Click the ⚙️ button 3 times in the Streamlit UI to enable debug mode
2. **Performance**: The system uses ChromaDB's HNSW index for fast similarity search
3. **AI Overviews**: Automatically generated when `enable_ai_overview=True` in `search_engine.py`
4. **Query Understanding**: The system auto-detects intent (definition, procedural, penalty, etc.)

---

**Last Updated**: After major cleanup on October 24, 2025
**System Status**: ✅ Fully functional and optimized


