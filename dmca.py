import os
from datetime import datetime
# reportlab is the PDF generation library
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER

NOTICES_FOLDER = "notices"  # folder where PDFs are saved

def generate_dmca_notice(owner_name, stolen_url, original_filename, watermark_id, detection_id):
    """
    Generates a DMCA takedown notice PDF.
    Returns the path to the generated PDF file.

    DMCA = Digital Millennium Copyright Act
    It's the legal process for requesting removal of stolen content.
    """

    # Create output filename with detection ID so each notice is unique
    output_filename = f"dmca_notice_{detection_id}.pdf"
    output_path = os.path.join(NOTICES_FOLDER, output_filename)

    # SimpleDocTemplate sets up the PDF with A4 paper size and margins
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # getSampleStyleSheet() gives us pre-made text styles
    styles = getSampleStyleSheet()

    # Create custom styles for our notice
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=12,
        spaceAfter=6,
        spaceBefore=12
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        leading=14  # line height
    )

    # Current date formatted nicely e.g. "January 15, 2025"
    today = datetime.now().strftime("%B %d, %Y")

    # Build the PDF content as a list of "story" elements
    # Paragraph() creates a text block, Spacer() adds blank space
    story = []

    # Title
    story.append(Paragraph("DMCA TAKEDOWN NOTICE", title_style))
    story.append(Paragraph("Digital Millennium Copyright Act — Section 512(c)", body_style))
    story.append(Spacer(1, 0.5*cm))

    # Date
    story.append(Paragraph(f"Date: {today}", body_style))
    story.append(Spacer(1, 0.3*cm))

    # Section 1: Claimant Info
    story.append(Paragraph("1. CLAIMANT INFORMATION", heading_style))
    story.append(Paragraph(f"Copyright Owner: <b>{owner_name}</b>", body_style))
    story.append(Paragraph(f"Platform: Sports Shield Protection System", body_style))
    story.append(Paragraph(f"Content ID: {watermark_id}", body_style))

    # Section 2: Infringing Content
    story.append(Paragraph("2. INFRINGING CONTENT", heading_style))
    story.append(Paragraph(
        f"The following URL contains content that infringes upon the copyright "
        f"of the claimant named above:",
        body_style
    ))
    story.append(Paragraph(f"Infringing URL: <b>{stolen_url}</b>", body_style))

    # Section 3: Original Content
    story.append(Paragraph("3. ORIGINAL CONTENT", heading_style))
    story.append(Paragraph(
        f"Original File: {original_filename}",
        body_style
    ))
    story.append(Paragraph(
        f"Watermark ID: {watermark_id} (embedded invisibly in the original content)",
        body_style
    ))
    story.append(Paragraph(
        "The original content was created by and belongs exclusively to the claimant. "
        "It has been digitally fingerprinted using Sports Shield's watermarking technology.",
        body_style
    ))

    # Section 4: Legal Statement
    story.append(Paragraph("4. GOOD FAITH STATEMENT", heading_style))
    story.append(Paragraph(
        "I have a good faith belief that the use of the material in the manner complained "
        "of is not authorized by the copyright owner, its agent, or the law.",
        body_style
    ))

    # Section 5: Accuracy Statement
    story.append(Paragraph("5. ACCURACY STATEMENT", heading_style))
    story.append(Paragraph(
        "The information in this notification is accurate, and under penalty of perjury, "
        "I am authorized to act on behalf of the owner of an exclusive right that is "
        "allegedly infringed.",
        body_style
    ))

    # Section 6: Requested Action
    story.append(Paragraph("6. REQUESTED ACTION", heading_style))
    story.append(Paragraph(
        "We request that you immediately remove or disable access to the infringing "
        "material listed above. Failure to respond may result in further legal action.",
        body_style
    ))

    # Signature section
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("_" * 40, body_style))
    story.append(Paragraph(f"Signature: {owner_name}", body_style))
    story.append(Paragraph(f"Date: {today}", body_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "Generated automatically by Sports Shield Protection System",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=8,
                      textColor=(0.5, 0.5, 0.5), alignment=TA_CENTER)
    ))

    # build() actually generates the PDF file from the story list
    doc.build(story)

    return output_path, output_filename
