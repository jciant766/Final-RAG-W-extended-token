# Reprocessing Guide

## ❓ Your Questions Answered

### 1. Will it embed files from `C:\Users\Jake\Desktop\Final RAG W TAx shi - Copy\Legislation`?

**Currently: NO** ❌

The `process_all_documents.py` script only processes:
- ✅ `malta_commercial_code_text.txt` (root folder)
- ✅ Text files in `ocr/output/*.txt`

**The 43 PDF files in the Legislation folder are NOT processed.**

### 2. Can we convert them to text files?

**YES!** ✅ I've created scripts to do this.

---

## 📁 Current Processing Status

### What's Currently Embedded (1,069 chunks):
```
✅ Commercial Code (Cap. 13) - 273 articles
✅ Companies Act (Cap. 386) - 462 articles
✅ 21 Subsidiary Legislation files (S.L. 386.XX) - 328 articles

Total: 23 documents, 1,063 articles, 1,069 chunks
```

### What's NOT Embedded (43 PDFs):
```
❌ All 43 PDF files in Legislation folder:
   - Civil Code, Income Tax Act, Land Registration Act
   - Notarial Profession Act, AIP Act, Condominium Act
   - Money Laundering Act, Real Estate Agents Act
   - And 35 more...
```

---

## 🚀 How to Reprocess & Add PDFs

### Option 1: Quick Delete & Rebuild (Current Docs Only)

**Simple delete and rebuild with existing text files:**

```bash
# Delete vector DB only
python delete_vector_db.py

# Database will rebuild automatically when you run:
streamlit run main.py
```

**Time:** ~3-4 minutes (automatic on app startup)

---

### Option 2: Full Reprocess (Convert PDFs + Rebuild)

**Convert PDFs to text and rebuild everything:**

```bash
# Step 1: Convert PDFs to text (one-time, ~5-20 minutes)
python convert_pdfs_to_text.py

# Step 2: Delete & reprocess everything
python reset_and_reprocess.py

# Step 3: Launch app (auto-builds vector DB)
streamlit run main.py
```

**Time:** 
- PDF conversion: ~5-20 minutes (one-time)
- Reprocessing: ~3-5 minutes
- Total: ~10-25 minutes

---

### Option 3: Complete Reset (Interactive)

**Guided process with prompts:**

```bash
python reset_and_reprocess.py
```

This script will:
1. Ask if you want to delete vector DB
2. Ask if you want to convert PDFs
3. Guide you through each step
4. Reprocess all documents

---

## 📋 Script Reference

### `delete_vector_db.py`
**Purpose:** Just delete the vector database  
**Use When:** You want to rebuild with existing text files  
**Time:** < 1 second  

```bash
python delete_vector_db.py
```

### `convert_pdfs_to_text.py`
**Purpose:** Convert PDFs from Legislation folder to text  
**Use When:** You want to add the 43 PDF files to your RAG  
**Time:** ~5-20 minutes  
**Output:** Text files in `ocr/output/`

```bash
python convert_pdfs_to_text.py
```

### `reset_and_reprocess.py`
**Purpose:** Complete reset - delete DB, optionally convert PDFs, reprocess all  
**Use When:** You want a fresh start with all documents  
**Time:** ~3-25 minutes (depending on options)

```bash
python reset_and_reprocess.py
```

### `process_all_documents.py`
**Purpose:** Reprocess all text files (no deletion)  
**Use When:** You added new text files and want to add them  
**Time:** ~3-5 minutes

```bash
python process_all_documents.py
streamlit run main.py  # Rebuild vector DB
```

---

## ⚙️ What Each Step Does

### 1. PDF Conversion (`convert_pdfs_to_text.py`)

**Input:**
```
Legislation/
├── 12 - Code of Organization and Civil Procedure.pdf
├── 123 - Income Tax Act.pdf
├── 16 - Civil Code.pdf
└── ... 40 more PDFs
```

**Output:**
```
ocr/output/
├── 12 - Code of Organization and Civil Procedure.txt
├── 123 - Income Tax Act.txt
├── 16 - Civil Code.txt
└── ... 40 more TXT files
```

**Uses:** Docling OCR library (already installed in `ocr/requirements.txt`)

### 2. Document Processing (`process_all_documents.py`)

**Processes:**
- `malta_commercial_code_text.txt`
- All `.txt` files in `ocr/output/`

**Creates:**
- `processed_chunks.json` (all chunks with metadata)
- `processing_report.json` (statistics)

**Each chunk contains:**
```json
{
  "id": "companies_act_article_123_p45_pos1_chunk_1",
  "content": "Article text here...",
  "metadata": {
    "article": "123",
    "page": 45,
    "citation": "Companies Act (Cap. 386) Art. 123",
    "document": "Companies Act (Cap. 386)",
    "doc_code": "companies_act",
    "doc_overview": "Companies Act (Cap. 386): Governs company formation...",
    "tokens": 250
  }
}
```

### 3. Vector DB Building (automatic in `main.py`)

**Happens when you run:** `streamlit run main.py`

**If no `chroma_db` folder exists:**
- Reads `processed_chunks.json`
- Generates embeddings for all chunks (using sentence transformers)
- Stores in ChromaDB vector database
- Takes ~3-4 minutes for 1,069 chunks

---

## 💡 Recommendations

### Scenario 1: Just want to rebuild existing data
```bash
python delete_vector_db.py
streamlit run main.py
```
**Time:** 3-4 minutes

### Scenario 2: Want to add the 43 PDF files
```bash
# First time only:
python convert_pdfs_to_text.py    # ~5-20 min
python delete_vector_db.py
python process_all_documents.py   # ~3-5 min
streamlit run main.py             # ~5-10 min for larger DB
```
**Total Time:** ~15-35 minutes  
**Result:** ~5,000-10,000 chunks (estimate) from 66 documents

### Scenario 3: Fresh start with everything
```bash
python reset_and_reprocess.py
# Follow prompts
streamlit run main.py
```

---

## 📊 Expected Results After Adding PDFs

### Current State (23 docs):
```
Documents: 23
Articles: 1,063
Chunks: 1,069
Embedding Time: ~3-4 minutes
```

### After Adding PDFs (66 docs):
```
Documents: 66 (23 existing + 43 new)
Articles: ~5,000-8,000 (estimate)
Chunks: ~5,000-10,000 (estimate)
Embedding Time: ~10-15 minutes
```

**Benefits:**
- ✅ Broader legal coverage (Civil Code, Tax Act, etc.)
- ✅ More comprehensive answers
- ✅ Better context for related topics

**Tradeoffs:**
- ⏱️ Longer initial load time (10-15 min vs 3-4 min)
- 💾 Larger database (~500MB vs ~100MB estimate)
- 🔍 May need better filtering to focus results

---

## 🔧 Troubleshooting

### "Docling not installed"
```bash
cd ocr
pip install -r requirements.txt
cd ..
```

### "No text files found"
Make sure text files are in:
- Project root: `malta_commercial_code_text.txt`
- OCR output: `ocr/output/*.txt`

### "Vector DB won't rebuild"
```bash
# Force delete and rebuild
python delete_vector_db.py
rm processed_chunks.json
rm processing_report.json
python process_all_documents.py
streamlit run main.py
```

### "PDF conversion is too slow"
- Normal! ~5-30 seconds per PDF
- You can convert in batches
- Once converted, you don't need to do it again

---

## ✅ Summary

| Question | Answer |
|----------|--------|
| **Will Legislation PDFs be embedded?** | No, not currently. They need to be converted to text first. |
| **Can we convert PDFs to text?** | Yes! Use `convert_pdfs_to_text.py` |
| **How to delete vector DB?** | Use `delete_vector_db.py` (simple) or `reset_and_reprocess.py` (complete) |
| **How to add PDF files?** | Convert → Process → Rebuild (see Option 2 above) |
| **Do I need to reprocess?** | Only if you want document overviews in metadata (optional) or want to add PDFs |

---

## 🎯 Quick Commands

```bash
# Quick delete & rebuild (existing data)
python delete_vector_db.py && streamlit run main.py

# Convert PDFs only
python convert_pdfs_to_text.py

# Full reset with PDFs
python convert_pdfs_to_text.py && python reset_and_reprocess.py

# Just reprocess (no delete)
python process_all_documents.py && streamlit run main.py
```


