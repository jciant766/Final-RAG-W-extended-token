import io
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from google.cloud import vision
from pdf2image import convert_from_path


@dataclass
class OCRBlock:
    text: str
    bounding_box: List[Tuple[int, int]]  # list of (x, y)
    page: int


def _vision_client() -> vision.ImageAnnotatorClient:
    # Requires GOOGLE_APPLICATION_CREDENTIALS to be set to a service account JSON
    return vision.ImageAnnotatorClient()


def _image_bytes_from_pil_image(pil_image) -> bytes:
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()


def _blocks_from_annotation(annotation, page_idx: int) -> List[OCRBlock]:
    blocks: List[OCRBlock] = []
    if not annotation or not annotation.full_text_annotation:
        return blocks

    for page in annotation.full_text_annotation.pages:
        # Use provided page index if single-page call; otherwise map actual page index
        actual_page_index = page_idx if page_idx is not None else 0
        for block in page.blocks:
            # Gather text for the block by concatenating symbols
            lines: List[str] = []
            for paragraph in block.paragraphs:
                words: List[str] = []
                for word in paragraph.words:
                    symbols = [s.text for s in word.symbols]
                    words.append("".join(symbols))
                lines.append(" ".join(words))

            text = "\n".join(l for l in lines if l.strip())
            vertices = [(v.x, v.y) for v in block.bounding_box.vertices]
            blocks.append(OCRBlock(text=text, bounding_box=vertices, page=actual_page_index + 1))

    return blocks


def ocr_image_bytes(image_bytes: bytes, page_index: int = 0) -> Dict[str, Any]:
    client = _vision_client()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    text = response.full_text_annotation.text if response.full_text_annotation else ""
    blocks = _blocks_from_annotation(response, page_idx=page_index)

    return {
        "text": text,
        "blocks": [
            {
                "text": b.text,
                "bounding_box": b.bounding_box,
                "page": b.page,
            }
            for b in blocks
        ],
    }


def ocr_pdf_local(pdf_path: str, poppler_path: Optional[str] = None, dpi: int = 300) -> Dict[str, Any]:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(pdf_path)

    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
    full_text_parts: List[str] = []
    all_blocks: List[Dict[str, Any]] = []

    for i, img in enumerate(images):
        img_bytes = _image_bytes_from_pil_image(img)
        result = ocr_image_bytes(img_bytes, page_index=i)
        # Add a clear page delimiter for downstream processing
        full_text_parts.append(f"--- PAGE {i+1} ---\n" + (result.get("text") or ""))
        all_blocks.extend(result.get("blocks", []))

    return {"text": "\n\n".join(full_text_parts).strip(), "blocks": all_blocks}


def ocr_image_file(image_path: str) -> Dict[str, Any]:
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    with open(image_path, "rb") as f:
        data = f.read()
    return ocr_image_bytes(data, page_index=0)


