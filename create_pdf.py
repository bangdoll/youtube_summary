
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_native_pdf(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, "Hello Gemini V4 Architecture")
    c.drawString(100, 730, "This is a native text layer.")
    c.drawString(100, 710, "It should be STRIPPED completely.")
    
    # Add a rectangle (vector graphic) that should Remain
    c.setFillColorRGB(0, 0, 1) # Blue
    c.rect(100, 600, 200, 100, fill=1)
    
    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_native_pdf("v4_native_source.pdf")
