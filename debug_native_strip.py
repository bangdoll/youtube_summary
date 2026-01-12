
import fitz
from PIL import Image
import io
import os

pdf_path = "Docs/Awakening_Blueprint.pdf"
output_path = "debug_vector_strip.png"

def test_strip():
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    page = doc.load_page(0) # First page
    
    # 1. Search for text to redact
    # We want to remove EVERYTHING that is text
    text_blocks = page.get_text("dict")["blocks"]
    count = 0
    for block in text_blocks:
        if block["type"] == 0: # Text
            for line in block["lines"]:
                for span in line["spans"]:
                    rect = fitz.Rect(span["bbox"])
                    page.add_redact_annot(rect, fill=False) # Transparent removal
                    count += 1
    
    print(f"Found {count} text spans to redact.")
    
    # 2. Apply redactions
    # images=2 (keep), graphics=2 (keep)
    page.apply_redactions(images=2, graphics=2, text=0)
    
    # 3. Render
    pix = page.get_pixmap(dpi=200)
    pix.save(output_path)
    print(f"Saved stripped image to {output_path}")

if __name__ == "__main__":
    test_strip()
