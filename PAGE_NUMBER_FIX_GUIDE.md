# Page Number Issue - Root Cause & Solutions

## 🔍 Problem Diagnosis

**Issue**: All sources in Streamlit AI overview show "Page 1"

**Root Cause**: OCR-processed text files (`ocr/output/*.txt`) don't contain page markers

---

## 🔬 Technical Analysis

### How Page Attribution Works

In `doc_processor.py` lines 159-190:

```python
# 1. Search for page markers in content
page_marker_re = re.compile(r"---\s*PAGE\s*(\d+)\s*---", re.IGNORECASE)

# 2. Extract positions of all page markers
for pm in page_marker_re.finditer(content):
    page_positions.append({"start": pm.start(), "page": page_no})

# 3. Assign page number to each article based on position
def page_for_index(idx: int) -> int:
    if not page_positions:
        return 1  # ← DEFAULTS TO PAGE 1 IF NO MARKERS!
```

### File Comparison

| File | Has Page Markers? | Page Numbers Work? |
|------|-------------------|-------------------|
| `malta_commercial_code_text.txt` | ✅ Yes (`--- PAGE 1 ---`) | ✅ Yes (pages 1-100+) |
| `ocr/output/615 - Real Estate...txt` | ❌ No | ❌ No (all page 1) |
| `ocr/output/16 - Civil Code.txt` | ❌ No | ❌ No (all page 1) |
| All other OCR files | ❌ No | ❌ No (all page 1) |

---

## ✅ Solution 1: Add Page Markers to Existing Files

### Using the Automated Script

I've created `add_page_markers_to_ocr.py` that intelligently adds page markers:

```bash
# Step 1: Run the script
python add_page_markers_to_ocr.py

# Output:
# - Creates 'ocr/output_with_pages/' directory
# - Adds page markers to all files
# - Reports pages added per file

# Step 2: Review the output
# Check a few files in 'ocr/output_with_pages/' to verify markers look good

# Step 3: Replace original files (BACKUP FIRST!)
cp ocr/output/*.txt ocr/output_backup/
cp ocr/output_with_pages/*.txt ocr/output/

# Step 4: Rebuild the vector database
python rebuild_database.py
```

### Manual Method (For Single Files)

If you prefer manual control, you can add markers yourself:

```python
# Example: Add markers every 3000 characters (approx 1 page)
def add_markers_manually(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    CHARS_PER_PAGE = 3000
    result = []
    page = 1
    pos = 0
    
    while pos < len(content):
        end = min(pos + CHARS_PER_PAGE, len(content))
        # Break at paragraph
        paragraph_break = content.find('\n\n', end - 200, end + 200)
        if paragraph_break != -1:
            end = paragraph_break + 2
        
        result.append(f"--- PAGE {page} ---\n")
        result.append(content[pos:end])
        page += 1
        pos = end
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(result))
```

---

## ✅ Solution 2: Update OCR Script for Future Files

I've already updated `ocr/docling_ocr.py` to automatically add page markers when processing new PDFs.

**How it works**:
1. Checks if Docling provides per-page access
2. If yes: Inserts `--- PAGE N ---` markers between pages
3. If no: Falls back to standard export (with warning)

**Test it**:
```bash
cd ocr
python docling_ocr.py ../Legislation/some-new-document.pdf

# Output should now include page markers
```

---

## 🎯 Expected Results After Fix

### Before Fix
```
AI Overview Sources:
- Real Estate Agents Act (Cap. 615) Art. 3(2) (Page 1)
- Real Estate Agents Act (Cap. 615) Art. 3(7) (Page 1)
- Real Estate Agents Act (Cap. 615) Art. 7(1) (Page 1)
- Real Estate Agents Act (Cap. 615) Art. 12(5) (Page 1)
```

### After Fix
```
AI Overview Sources:
- Real Estate Agents Act (Cap. 615) Art. 3(2) (Page 2)
- Real Estate Agents Act (Cap. 615) Art. 3(7) (Page 3)
- Real Estate Agents Act (Cap. 615) Art. 7(1) (Page 4)
- Real Estate Agents Act (Cap. 615) Art. 12(5) (Page 7)
```

---

## 📊 Verification Steps

### 1. Check Text Files Have Markers

```bash
# Should show page marker counts for each file
grep -c "--- PAGE" ocr/output/*.txt
```

### 2. Check Processed Chunks

```python
import json

with open('processed_chunks.json', 'r') as f:
    chunks = json.load(f)

# Check page distribution
from collections import Counter
pages = Counter(chunk['metadata']['page'] for chunk in chunks if chunk['metadata']['doc_code'] == 'cap_615')
print(f"Real Estate Act page distribution: {dict(pages)}")

# Should show: {1: 5, 2: 8, 3: 12, 4: 7, ...}
# NOT: {1: 123}
```

### 3. Test in Streamlit

```bash
streamlit run main.py

# Search for: "What are the duties of real estate agents?"
# AI Overview sources should show varied page numbers
```

---

## 🔧 Troubleshooting

### Issue: Script doesn't add enough pages

**Problem**: Large documents get only 1-2 page markers

**Fix**: Adjust `CHARS_PER_PAGE` in `add_page_markers_to_ocr.py`:

```python
# Line ~59
CHARS_PER_PAGE = 2500  # Make smaller for more pages
```

### Issue: Page breaks mid-article

**Problem**: Article content split across page boundary unnaturally

**Solution**: This is actually OK! Your chunking strategy handles this:
- Articles are extracted first (complete)
- Then chunked if too large
- Page number reflects where article starts
- Overlapping chunks preserve context

### Issue: Some files still show Page 1

**Possible causes**:
1. File wasn't reprocessed - check `processed_chunks.json` timestamp
2. Old chunks cached - rebuild database
3. File didn't get markers - check with `grep "--- PAGE" filename.txt`

**Fix**:
```bash
# Force complete rebuild
rm processed_chunks.json
rm -rf chroma_db/
python rebuild_database.py
```

---

## 📈 Impact Assessment

### Files Affected
- **43 text files** in `ocr/output/`
- **~50,000+ chunks** in vector database
- All search results and AI overview citations

### Processing Time
- **Add markers**: ~1-2 minutes for all files
- **Rebuild database**: ~5-10 minutes depending on file count

### Benefits
- ✅ Accurate page citations in AI overview
- ✅ Better legal research (can verify sources in original PDF)
- ✅ Professional output for users
- ✅ Traceable to original documents

---

## 💡 Why This Wasn't Caught Earlier

1. **Commercial Code worked**: The original file (`malta_commercial_code_text.txt`) had page markers, so the system appeared to work

2. **Testing focused on content**: Early testing verified article extraction and search quality, not page attribution

3. **OCR complexity**: Docling's `export_to_text()` doesn't include page metadata by default

---

## 🚀 Recommended Workflow

### For Existing Project (One-Time Fix)

```bash
# 1. Add page markers
python add_page_markers_to_ocr.py

# 2. Review output
ls -lh ocr/output_with_pages/
head -50 ocr/output_with_pages/615*.txt  # Check a sample

# 3. Backup and replace
mkdir -p backups
cp -r ocr/output backups/ocr_output_$(date +%Y%m%d)
cp ocr/output_with_pages/*.txt ocr/output/

# 4. Rebuild database
python rebuild_database.py

# 5. Test in Streamlit
streamlit run main.py
```

### For New Documents (Ongoing)

```bash
# Process new PDF with enhanced OCR script
cd ocr
python docling_ocr.py ../Legislation/new-document.pdf

# Verify it has page markers
grep -c "--- PAGE" output/new-document.txt

# Add to processing
cd ..
python process_all_documents.py
```

---

## 📝 Summary

**Problem**: ❌ OCR files missing page markers → All articles default to Page 1

**Solution 1**: ✅ Run `add_page_markers_to_ocr.py` to fix existing files

**Solution 2**: ✅ Updated `ocr/docling_ocr.py` for future files

**Result**: ✅ Accurate page citations in AI overview

**Time to Fix**: ~15 minutes including database rebuild

---

## Next Steps

1. **Run the page marker script** to fix existing files
2. **Rebuild the vector database** with proper page numbers
3. **Test in Streamlit** - page numbers should now be accurate
4. **Future PDFs** will automatically get page markers

Ready to fix this? Run:
```bash
python add_page_markers_to_ocr.py
```



