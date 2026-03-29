import base64
import fitz  # PyMuPDF


# Models known to support vision (image_url input)
VISION_MODELS = {
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-turbo",
    "anthropic/claude-opus-4",
    "anthropic/claude-sonnet-4-5",
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-3-5-sonnet",
    "anthropic/claude-3-5-haiku",
    "google/gemini-2.0-flash-001",
    "google/gemini-pro-1.5",
    "moonshotai/kimi-k2",
}

# Prefix match (e.g. "openai/gpt-4" matches "openai/gpt-4o-2024-...")
VISION_PREFIXES = (
    "openai/gpt-4",
    "anthropic/claude",
    "google/gemini",
    "moonshotai/kimi",
    "qwen/qwen-vl",
    "qwen/qwen2-vl",
    "qwen/qwen2.5-vl",
    "meta-llama/llama-4",
)


def model_supports_vision(model_id: str) -> bool:
    if model_id in VISION_MODELS:
        return True
    return any(model_id.startswith(p) for p in VISION_PREFIXES)


def extract_text_from_bytes(pdf_bytes: bytes, max_chars: int = 40000) -> str:
    """Extract plain text from PDF. Truncated to max_chars."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    total = 0
    for i, page in enumerate(doc, 1):
        text = page.get_text().strip()
        if text:
            pages_text.append(f"[第{i}页]\n{text}")
            total += len(text)
        if total >= max_chars:
            pages_text.append(f"\n...(文本超过{max_chars}字符，已截断)...")
            break
    doc.close()
    return "\n\n".join(pages_text)


def render_pages_as_images(
    pdf_bytes: bytes,
    dpi: int = 150,
    max_pages: int = 20,
) -> list[str]:
    """
    Render each PDF page as a base64-encoded PNG.
    Returns a list of base64 strings (one per page).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    n = min(len(doc), max_pages)
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 dpi is PDF default
    for i in range(n):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        png_bytes = pix.tobytes("png")
        images.append(base64.b64encode(png_bytes).decode("utf-8"))
    doc.close()
    return images


def extract_from_base64(pdf_base64: str):
    """Return (pdf_bytes, text, page_images_b64_list)."""
    pdf_bytes = base64.b64decode(pdf_base64)
    text = extract_text_from_bytes(pdf_bytes)
    page_images = render_pages_as_images(pdf_bytes)
    return pdf_bytes, text, page_images
