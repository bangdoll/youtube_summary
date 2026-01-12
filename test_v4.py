
import logging
import asyncio
from native_pdf import PdfRenderer

logging.basicConfig(level=logging.INFO)

async def test_vector_stripping():
    import glob
    import os
    
    pdfs = glob.glob("*.pdf") + glob.glob("Docs/*.pdf")
    found_native = False
    
    if not pdfs:
        print("No PDFs found.")
        return

    for pdf_path in pdfs:
        try:
            print(f"--- Checking {pdf_path} ---")
            renderer = PdfRenderer(pdf_path)
            count = renderer.get_page_count()
            if count == 0: continue
            
            # Check first few pages
            for i in range(min(count, 3)):
                text = renderer.extract_text(i)
                if len(text) > 0: # Threshold to consider as "Native"
                    print(f"Found Native PDF! {pdf_path} (Page {i} has {len(text)} items)")
                    # Run Verification
                    img = renderer.get_clean_image(i)
                    print(f"Clean Image Generated: {img.size}")
                    img.save(f"v4_verify_{os.path.basename(pdf_path)}_{i}.png")
                    print("Verification Successful.")
                    found_native = True
                    break
            renderer.close()
            if found_native: break
        except Exception as e:
            print(f"Error checking {pdf_path}: {e}")
            
    if not found_native:
        print("No Native PDF found in directory.")

if __name__ == "__main__":
    asyncio.run(test_vector_stripping())
