Standalone Docling OCR
======================

Usage
-----

1) Create a virtual environment (recommended) and install requirements:

```
python -m venv .venv
.venv\\Scripts\\activate
pip install -r ocr/requirements.txt
```

2) Run OCR on one or more legal document URLs (PDF):

```
python ocr/docling_ocr.py "https://example.com/legal.pdf" "https://example.com/another.pdf"
```

3) Output `.txt` files will be saved under `ocr/output` by default. Override with `--out`:

```
python ocr/docling_ocr.py https://example.com/legal.pdf --out extracted_text
```

Notes
-----

- This script is standalone and not integrated with the main app.
- It relies on Docling's `DocumentConverter` to convert PDFs to text. If Docling import fails, check installation or adjust the import to match your installed Docling version.
- For very large PDFs, the script streams the download and writes progressively to disk.


Google Cloud Vision OCR
-----------------------

Feasibility: Yes. Google Cloud Vision (Document Text Detection) reliably extracts legal text and, with page/block/paragraph/word hierarchy, can preserve layout well enough to reconstruct tables and forms. For perfect table fidelity you usually pair OCR with layout reconstruction logic; this repo includes bounding boxes per block to enable that downstream.

Setup:

1) Enable Vision API in your GCP project and create a service account with Vision access.
2) Download the JSON key and set the environment variable:

```
set GOOGLE_APPLICATION_CREDENTIALS=path\to\service_account.json
```

3) Install requirements:

```
pip install -r ocr/requirements.txt
```

Run (Directory "file bot"):

```
python ocr/file_bot.py input_dir --out ocr/output --poppler C:\\path\\to\\poppler\\Library\\bin
```

- Accepts PDFs and images; writes `<name>.txt` and `<name>_extracted.json` plus an `index.json`.
- `_extracted.json` contains basic heuristics (articles detected, definitions, requirements, penalties). For production-grade legal extraction, wire this into `statutory_extractor.py`.

Single PDF:

```
python ocr/file_bot.py path\to\file.pdf --out ocr/output
```


