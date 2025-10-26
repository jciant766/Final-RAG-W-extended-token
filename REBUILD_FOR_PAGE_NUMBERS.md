# Fix Page Numbers - Rebuild Instructions

## Current Status

**GOOD NEWS**: 34 out of 43 documents (79%) already have page markers!

The page numbers aren't showing because your vector database was built before page markers were added.

## Files WITH Page Markers (34 files - 79%)
These will show correct page numbers after rebuild:
- 12 - Code of Organization and Civil Procedure.txt: 276 pages
- 123 - Income Tax Act.txt: 46 pages
- 123.27 - Capital Gains Rules.txt: 47 pages
- 16 - Civil Code.txt: 385 pages
- 364 - Duty on Documents and Transfers Act.txt: 25 pages
- 55 - Notarial Profession and Notarial Archives Act.txt: 59 pages
- And 28 more...

## Files WITHOUT Page Markers (9 files - 21%)
These are small documents (1-3 pages) that will show "Page 1":
- 123.198 - Assignments of Rights
- 246.04 - AIP Values
- 364.01 - Old Duty Exemptions
- 364.17 - Second Time Buyers
- 364.18 - New Causa Mortis Interest Rate
- 398 - Condominium Act
- 540 - Gender Identity Act
- 55.05 - Acts of Deceased Notaries
- 55.06 - Examination of Title

---

## Quick Fix - Rebuild Vector Database

**This will fix 79% of your page number issues immediately!**

### Step 1: Delete old vector database
```bash
python delete_vector_db.py
```

### Step 2: Rebuild with page markers
```bash
python build_vector_db.py
```

### Step 3: Test in Streamlit
```bash
streamlit run main.py
```

**That's it!** Your page numbers will now show correctly for 34/43 documents.

---

## Optional: Fix the Remaining 9 Files

If you want 100% coverage, add page markers to the 9 missing files.

Most are very short (1-3 pages), so you can:

1. **Check actual page count** in the PDF
2. **Add markers manually**:
   ```
   --- PAGE 1 ---
   [content]

   --- PAGE 2 ---
   [content]
   ```

3. **Rebuild again**:
   ```bash
   python delete_vector_db.py
   python build_vector_db.py
   ```

---

## Why This Happened

Your documents were converted from PDF to text with page markers.
But your vector database was built BEFORE those conversions were complete.

Simply rebuilding picks up all the existing page markers.

---

## Expected Result After Rebuild

**Before Rebuild:**
- All citations show "Page 1"
- Users can't find specific page references

**After Rebuild:**
- 79% of citations show accurate page numbers
- Users can locate exact provisions in source documents
- Professional legal research experience

**Example Output:**
```
Sources Referenced:
- Civil Code (Cap. 16) — Art. 1123 (Page 187)
- Income Tax Act (Cap. 123) — Art. 4 (Page 12)
- Companies Act (Cap. 386) — Art. 141 (Page 56)
```

---

## Estimated Time

- Delete DB: 10 seconds
- Rebuild DB: 2-5 minutes
- Total: ~5 minutes

**Your page numbers will be fixed!**
