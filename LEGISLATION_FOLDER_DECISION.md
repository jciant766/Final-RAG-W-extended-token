# ⚠️ DECISION NEEDED: Legislation Folder

## 📋 Current Status

You have **43 PDF files** in the `Legislation/` folder that are **NOT being processed** by your RAG system.

---

## 🤔 Question: What Should You Do?

### Option A: **Keep and Process These PDFs**

**If these PDFs contain important legal documents you want searchable:**

1. **Move PDFs to OCR input folder:**
   ```powershell
   Move-Item -Path "Legislation\*.pdf" -Destination "ocr\input_pdfs\"
   ```

2. **Run OCR conversion:**
   ```powershell
   cd ocr
   python docling_ocr.py
   ```

3. **Delete the now-empty Legislation folder:**
   ```powershell
   cd ..
   Remove-Item -Recurse -Force Legislation
   ```

4. **Restart your Streamlit app** - it will auto-detect new text files and rebuild the database

**Pros:**
- Makes all 43 legal documents searchable
- Comprehensive legal knowledge base

**Cons:**
- Takes time to process
- Increases database size
- More API costs (OpenAI embeddings)

---

### Option B: **Delete These PDFs (They're Duplicates or Unnecessary)**

**If these PDFs are:**
- Already in your `ocr/input_pdfs/` folder
- Not relevant to your legal search system
- Backup copies you don't need

**Then simply delete:**
```powershell
Remove-Item -Recurse -Force Legislation
```

---

## 🔍 How to Check if They're Duplicates

Compare filenames:
```powershell
# List PDFs in Legislation folder
Get-ChildItem -Path "Legislation\*.pdf" | Select-Object Name

# List PDFs already in OCR input
Get-ChildItem -Path "ocr\input_pdfs\*.pdf" | Select-Object Name

# Compare manually to see if there's overlap
```

---

## 📊 Current System Summary

**Currently Indexed (22 documents):**
- ✅ Commercial Code (Cap. 13)
- ✅ Companies Act (Cap. 386)
- ✅ Subsidiary Legislation 386.02 through 386.24
- ✅ Subsidiary Legislation 595.27

**Not Yet Indexed (43 documents):**
- ❓ Whatever is in `Legislation/` folder

---

## 💡 My Recommendation

1. **Check the filenames** in both locations
2. **If they're duplicates** → Delete `Legislation/` folder
3. **If they're new documents** → Move to `ocr/input_pdfs/` and process
4. **If you're unsure** → Keep them for now, but they won't be searchable until processed

---

**Your decision determines the scope of your legal search system!**


