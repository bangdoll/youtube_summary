import fitz  # PyMuPDF
from PIL import Image
import io
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class PdfRenderer:
    def __init__(self, pdf_path: str):
        self.doc = fitz.open(pdf_path)

    def get_page_count(self) -> int:
        return len(self.doc)

    def get_clean_image(self, page_index: int, dpi: int = 200) -> Image.Image:
        """
        Renders the page WITHOUT text options.
        Strategy: Set text rendering mode to invisible (3) or simply don't render text objects.
        PyMuPDF allows suppressing text via flags or custom display list.
        But a simpler way for 100% reliable stripping is to iterate through separate drawing paths?
        
        Better approach with PyMuPDF:
        We can use `page.get_drawings()` to redraw everything EXCEPT text.
        Or simpler: modify the PDF page in memory to remove text blocks, then render.
        
        Best approach for "Vector Stripping":
        1. Load page.
        2. Clean contents: remove text operators.
        3. Render.
        """
        try:
            page = self.doc.load_page(page_index)
            
            # Create a temporary copy of the page to modify
            # Actually, fitz allows 'redacting' text properly or implementing a filter.
            # But 'redaction' usually leaves white bars. We want BACKGROUND.
            
            # Strategy: Use DisplayList
            dl = page.get_displaylist()
            # Render valid contents manually? No, DisplayList is opaque.
            
            # Strategy: "clean_contents()" sanitizes the content stream.
            # But to remove text, we can use `page.add_redact_annot(rect)` + `page.apply_redactions(images=0, graphics=0)`
            # If we set text color to transparent? No, it might still obscure.
            
            # The most robust way:
            # Iterate over all text instances and mark them for redaction (removal).
            # Then apply redactions with options to NOT redact images/graphics.
            
            text_instances = page.search_for("") # Get all text? No, search_for returns rects.
            # We want ALL text.
            
            # Method: page.get_text("dict") -> blocks -> precise bboxes
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0: # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            rect = fitz.Rect(span["bbox"])
                            # Add redaction annotation
                            # fill=None ensures we see what's behind (if possible) or just remove the object.
                            # Actually, apply_redactions() REMOVES the content commands.
                            # So the text object is GONE.
                            page.add_redact_annot(rect, fill=False) # fill=False means transparent/removed
            
            # Apply redactions: render text as invisible/removed.
            # images=0 (default) -> Remove overlapped images. We want to KEEP them.
            # images=2 (PDF_REDACT_IMAGE_NONE) -> Do not remove images.
            # graphics=2 (PDF_REDACT_GRAPHICS_NONE) -> Do not remove vector graphics.
            
            # Constants might vary by version.
            # 0 = remove
            # 1 = remove content but keep space?
            # 2 = ignore (keep content)
            
            # Using integer 2 for safety if constants are missing
            page.apply_redactions(images=2, graphics=2)
            
            # Now render the page
            pix = page.get_pixmap(dpi=dpi)
            img_data = pix.tobytes("png")
            return Image.open(io.BytesIO(img_data))
            
        except Exception as e:
            logger.error(f"Vector stripping failed for page {page_index}: {e}")
            raise

    def extract_text(self, page_index: int) -> list:
        """
        Returns structured text with sorting.
        PyMuPDF's "dict" or "blocks" is very good.
        """
        try:
            page = self.doc.load_page(page_index)
            # flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE
            blocks = page.get_text("dict", sort=True)["blocks"]
            
            text_data = []
            for block in blocks:
                if block["type"] == 0: # Text
                     for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():
                                text_data.append({
                                    "text": span["text"],
                                    "bbox": span["bbox"], # (x0, y0, x1, y1)
                                    "size": span["size"],
                                    "font": span["font"],
                                    "color": span["color"]
                                })
            return text_data
        except Exception as e:
            logger.error(f"Text extraction failed for page {page_index}: {e}")
            return []

    def close(self):
        if self.doc:
            self.doc.close()


# Legacy Helper Functions (Adapter for existing code if needed, but we should switch to class usage)
def get_pdf_renderer(pdf_path):
    return PdfRenderer(pdf_path)

def get_page_size(pdf_path: str, page_index: int) -> Tuple[float, float]:
    """Returns (width, height) in points."""
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_index)
        size = page.rect
        doc.close()
        return (float(size.width), float(size.height))
    except Exception as e:
        logger.error(f"Error getting page size for {pdf_path} page {page_index}: {e}")
        return (0, 0)

def extract_text_and_coordinates(pdf_path: str, page_index: int) -> List[Dict]:
    """
    Extracts text and coordinates from a specific page of a PDF using PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file.
        page_index: Index of the page to extract (0-based).
        
    Returns:
        List of dictionaries containing 'text' and 'bbox' (x0, y0, x1, y1).
        Coordinates are in PDF Point units (usually 1/72 inch).
        Returns empty list if no text found or an error occurs.
    """
    renderer = None
    try:
        renderer = PdfRenderer(pdf_path)
        text_data = renderer.extract_text(page_index)
        
        results = []
        for item in text_data:
            results.append({
                'text': item['text'],
                'bbox_pdf': item['bbox'], # PyMuPDF returns (x0, y0, x1, y1) directly
                'font_size': item['size']
                # 'tm' is not directly available in this format, but bbox is more useful
            })
        return results
    except Exception as e:
        logger.error(f"PyMuPDF Extraction Error for {pdf_path} page {page_index}: {e}")
        return []
        return (float(page.mediabox.width), float(page.mediabox.height))
    except:
        return (0, 0)
