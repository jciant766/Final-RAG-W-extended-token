# 🚀 Quick Start Guide - Malta Legal RAG System

## ✅ Your System is Clean and Ready!

---

## 🎯 What Your RAG System Does

Your system is a **smart legal search engine** for Malta commercial law that:
1. **Understands natural language queries** ("What are the duties of a director?")
2. **Finds relevant articles** using AI-powered semantic search
3. **Generates summaries** with citations from the actual legal text
4. **Displays results** in a beautiful web interface

---

## 🏃 Run Your System

### Start the Streamlit App:
```bash
streamlit run main.py
```

Then open your browser to: `http://localhost:8501`

---

## 📚 What's Currently Searchable

Your system has **22 legal documents** indexed:
- ✅ Commercial Code (Cap. 13)
- ✅ Companies Act (Cap. 386)  
- ✅ Subsidiary Legislation 386.02-386.24 (20 files)
- ✅ Subsidiary Legislation 595.27

---

## 🔍 Example Queries

Try searching for:
- **Definitions**: "What is a trader?"
- **Procedures**: "How to register a company?"
- **Requirements**: "Director duties under Companies Act"
- **Specific Articles**: "Article 477"
- **Penalties**: "Late payment penalties"

---

## 📂 Core Files (Never Delete These)

### Application Files:
- `main.py` - Your Streamlit web app
- `doc_processor.py` - Processes legal documents
- `vector_store.py` - ChromaDB vector database
- `search_engine.py` - Smart search with query understanding
- `ai_assistant.py` - AI overview generation
- `debug_logger.py` - Logging system

### Data Files:
- `chroma_db/` - Vector database (your embeddings)
- `ocr/output/` - Converted text files (22 documents)
- `processed_chunks.json` - Processed chunks
- `env` - Environment variables (API keys)

---

## 🆕 Add New Documents

### Step 1: Add PDFs
Place PDF files in: `ocr/input_pdfs/`

### Step 2: Convert to Text
```bash
cd ocr
python docling_ocr.py
```

### Step 3: Rebuild Database
Delete these to trigger rebuild:
- `chroma_db/` folder
- `processed_chunks.json`

### Step 4: Restart
```bash
streamlit run main.py
```

The system will automatically:
- Process new text files
- Extract articles
- Create chunks
- Generate embeddings
- Build vector database

---

## ⚙️ Configuration

### Environment Variables (in `env` file):
```
OPENAI_API_KEY=your_api_key_here
```

### Chunking Settings (in `doc_processor.py`):
- **Chunk Size**: 3000 tokens
- **Overlap**: 200 tokens

### AI Models:
- **Embeddings**: `text-embedding-3-large` (OpenAI)
- **Summaries**: `gpt-4o-mini` (OpenAI)

---

## 🐛 Troubleshooting

### No Results Found?
- Check `debug_logs/queries.log` for search queries
- Check `debug_logs/search_engine.log` for results
- Enable debug mode: Click ⚙️ button 3x in UI

### Database Empty?
- Delete `chroma_db/` and restart
- System will auto-rebuild from `processed_chunks.json`

### New PDFs Not Appearing?
1. Verify they're in `ocr/input_pdfs/`
2. Run `python ocr/docling_ocr.py`
3. Check `ocr/output/` for .txt files
4. Delete `chroma_db/` to force rebuild

---

## 📊 System Stats

**Files Cleaned Up**: 
- Deleted 4 folders (deprecated, scripts, dashboards, test_chunking)
- Deleted 12 unused files
- Removed test/demo/cache directories

**Current State**:
- ✅ Clean, organized structure
- ✅ Only essential files remain
- ✅ Fully functional RAG system
- ✅ 22 legal documents indexed

---

## 🎓 Learn More

Read the full documentation:
- `PROJECT_STRUCTURE.md` - Complete system architecture
- `LEGISLATION_FOLDER_DECISION.md` - What to do with unprocessed PDFs
- `README.md` - Original project README
- `ocr/README.md` - OCR processing guide

---

## 💡 Pro Tips

1. **Debug Mode**: Hidden debug panel shows query analysis and system stats
2. **Intent Detection**: System auto-detects if you want definitions, procedures, penalties, etc.
3. **Citation Tracking**: AI summaries include exact article citations and page numbers
4. **Multi-Document Search**: Searches across Commercial Code, Companies Act, and Subsidiary Legislation
5. **Chunk Reconstruction**: Long articles split into chunks are automatically merged in results

---

**🎉 Your RAG system is ready to use! Happy searching!**


