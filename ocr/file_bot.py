import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any

from gcv_ocr import ocr_pdf_local, ocr_image_file


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def simple_legal_extract(full_text: str) -> Dict[str, Any]:
    """Very light heuristic extraction placeholders. For production, integrate your statutory_extractor."""
    data: Dict[str, Any] = {
        "articles_detected": [],
        "definitions": [],
        "requirements": [],
        "penalties": [],
    }

    # Detect article headings like "123." or "26A." at line starts
    import re
    for m in re.finditer(r"(?m)^[\t \u00A0]*([0-9]{1,4}[A-Z]?)\s*\.", full_text):
        data["articles_detected"].append(m.group(1))

    # Naive patterns
    for m in re.finditer(r"\b([A-Za-z][A-Za-z\- ]{2,30})\b\s+means\s+([^\.;\n]{5,200})", full_text, flags=re.IGNORECASE):
        data["definitions"].append({"term": m.group(1).strip(), "definition": m.group(2).strip()})

    for m in re.finditer(r"\b(shall|must|is required to)\b[^\.\n]{0,200}", full_text, flags=re.IGNORECASE):
        data["requirements"].append({"text": m.group(0).strip()})

    for m in re.finditer(r"\b(penalty|fine|imprisonment)\b[^\.\n]{0,200}", full_text, flags=re.IGNORECASE):
        data["penalties"].append({"text": m.group(0).strip()})

    return data


def process_file(path: Path, out_dir: Path, poppler_path: str | None) -> Dict[str, Any]:
    ext = path.suffix.lower()
    result: Dict[str, Any]
    if ext == ".pdf":
        result = ocr_pdf_local(str(path), poppler_path=poppler_path)
    else:
        result = ocr_image_file(str(path))

    # Write text
    txt_out = out_dir / f"{path.stem}.txt"
    with txt_out.open("w", encoding="utf-8") as f:
        f.write(result.get("text", ""))

    # Simple extraction placeholder
    extracted = simple_legal_extract(result.get("text", ""))
    json_out = out_dir / f"{path.stem}_extracted.json"
    with json_out.open("w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)

    return {"text_path": str(txt_out), "json_path": str(json_out)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Process PDFs/images with Google Cloud Vision OCR and write outputs")
    parser.add_argument("input", help="Input path: file or directory")
    parser.add_argument("--out", default="ocr/output", help="Output directory")
    parser.add_argument("--poppler", default=None, help="Poppler path for pdf2image on Windows (optional)")
    args = parser.parse_args()

    inp = Path(args.input)
    out_dir = Path(args.out)
    ensure_dir(out_dir)

    targets: List[Path] = []
    if inp.is_dir():
        for p in inp.iterdir():
            if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
                targets.append(p)
    elif inp.is_file():
        targets.append(inp)
    else:
        raise SystemExit(f"Input path not found: {inp}")

    results: List[Dict[str, Any]] = []
    for t in targets:
        try:
            r = process_file(t, out_dir, args.poppler)
            print(f"Processed: {t} -> {r['text_path']}, {r['json_path']}")
            results.append({"file": str(t), **r})
        except Exception as e:
            print(f"ERROR processing {t}: {e}")

    # Index file listing
    index_path = out_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote index: {index_path}")


if __name__ == "__main__":
    main()
