from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def generate_takedown(owner_name, stolen_url, original_url):
    """Creates a professional DMCA Takedown PDF."""
    filename = f"takedown_{owner_name}.pdf"
    filepath = os.path.join('static/notices/', filename)
    
    if not os.path.exists('static/notices/'):
        os.makedirs('static/notices/')

    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "OFFICIAL DMCA TAKEDOWN NOTICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Date: 2026-04-25")
    c.drawString(100, 700, f"From: {owner_name} (Verified StampIt User)")
    c.drawString(100, 680, f"Subject: Unauthorized use of copyrighted sports media.")
    
    text = f"It has come to our attention that the content at {stolen_url} is a stolen copy of the original content located at {original_url}. This video was stamped with an invisible identity key via StampIt."
    
    # Simple text wrapping
    c.drawString(100, 650, text[:60])
    c.drawString(100, 635, text[60:120])
    
    c.drawString(100, 600, "Please remove this content immediately to avoid legal action.")
    c.save()
    
    return filename
