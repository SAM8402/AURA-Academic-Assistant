"""
PDF Export Service for Slide Decks
Generates styled PDF documents with themes, colors, and embedded charts.
"""

from io import BytesIO
import base64
import re
from typing import List, Optional
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas


class PDFSlideTheme:
    """Defines a visual theme for PDF slides."""
    def __init__(
        self,
        name: str,
        bg_color: colors.Color,
        title_color: colors.Color,
        text_color: colors.Color,
        accent_color: colors.Color,
        font_title: str = "Helvetica-Bold",
        font_body: str = "Helvetica"
    ):
        self.name = name
        self.bg_color = bg_color
        self.title_color = title_color
        self.text_color = text_color
        self.accent_color = accent_color
        self.font_title = font_title
        self.font_body = font_body


# Predefined themes matching PPTX themes
PDF_THEMES = {
    "professional": PDFSlideTheme(
        name="Professional",
        bg_color=colors.white,
        title_color=colors.HexColor("#1F4E78"),  # Navy Blue
        text_color=colors.HexColor("#404040"),   # Dark Gray
        accent_color=colors.HexColor("#4472C4"),  # Blue
        font_title="Helvetica-Bold",
        font_body="Helvetica"
    ),
    "modern": PDFSlideTheme(
        name="Modern",
        bg_color=colors.HexColor("#F8F9FA"),     # Light Gray
        title_color=colors.HexColor("#0D6EFD"),  # Bright Blue
        text_color=colors.HexColor("#212529"),   # Almost Black
        accent_color=colors.HexColor("#6F42C1"),  # Purple
        font_title="Helvetica-Bold",
        font_body="Helvetica"
    ),
    "colorful": PDFSlideTheme(
        name="Colorful",
        bg_color=colors.HexColor("#FFF8F0"),     # Peach
        title_color=colors.HexColor("#DC3545"),  # Red
        text_color=colors.HexColor("#343A40"),   # Dark Gray
        accent_color=colors.HexColor("#FD7E14"),  # Orange
        font_title="Times-Bold",
        font_body="Times-Roman"
    ),
    "dark": PDFSlideTheme(
        name="Dark",
        bg_color=colors.HexColor("#212529"),     # Dark Gray
        title_color=colors.HexColor("#FFC107"),  # Yellow
        text_color=colors.HexColor("#F8F9FA"),   # White
        accent_color=colors.HexColor("#20C997"),  # Teal
        font_title="Helvetica-Bold",
        font_body="Helvetica"
    ),
    "minimalist": PDFSlideTheme(
        name="Minimalist",
        bg_color=colors.HexColor("#FAFAFA"),     # Off-White
        title_color=colors.black,
        text_color=colors.HexColor("#606060"),   # Gray
        accent_color=colors.HexColor("#909090"),  # Light Gray
        font_title="Helvetica-Bold",
        font_body="Helvetica"
    )
}


class SlidePage:
    """Custom page template for slide-like PDF pages."""
    
    def __init__(self, theme: PDFSlideTheme):
        self.theme = theme
    
    def __call__(self, canvas_obj, doc):
        """Draw the page background."""
        canvas_obj.saveState()
        
        # Fill background
        canvas_obj.setFillColor(self.theme.bg_color)
        canvas_obj.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=True, stroke=False)
        
        canvas_obj.restoreState()


class PDFExportService:
    """Service for exporting slide decks to PDF format with styling."""
    
    def __init__(self, theme_name: str = "professional"):
        """Initialize with a theme."""
        self.theme = PDF_THEMES.get(theme_name.lower(), PDF_THEMES["professional"])
        self.page_width = landscape(A4)[0]
        self.page_height = landscape(A4)[1]
        self.styles = self._create_styles()
    
    def _create_styles(self):
        """Create custom paragraph styles matching the theme."""
        styles = getSampleStyleSheet()
        
        # Title slide - main title
        styles.add(ParagraphStyle(
            name='TitleMain',
            parent=styles['Title'],
            fontSize=44,
            textColor=self.theme.title_color,
            fontName=self.theme.font_title,
            alignment=TA_CENTER,
            spaceAfter=30,
            leading=52
        ))
        
        # Title slide - subtitle
        styles.add(ParagraphStyle(
            name='TitleSub',
            parent=styles['Normal'],
            fontSize=24,
            textColor=self.theme.text_color,
            fontName=self.theme.font_body,
            alignment=TA_CENTER,
            leading=32
        ))
        
        # Content slide - title
        styles.add(ParagraphStyle(
            name='SlideTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=self.theme.title_color,
            fontName=self.theme.font_title,
            alignment=TA_LEFT,
            spaceAfter=20,
            leftIndent=40,
            leading=34
        ))
        
        # Content slide - body text
        styles.add(ParagraphStyle(
            name='SlideBody',
            parent=styles['Normal'],
            fontSize=14,
            textColor=self.theme.text_color,
            fontName=self.theme.font_body,
            alignment=TA_LEFT,
            spaceAfter=10,
            leftIndent=60,
            leading=20
        ))
        
        # Content slide - bullet points
        styles.add(ParagraphStyle(
            name='SlideBullet',
            parent=styles['Normal'],
            fontSize=14,
            textColor=self.theme.text_color,
            fontName=self.theme.font_body,
            alignment=TA_LEFT,
            leftIndent=80,
            bulletIndent=60,
            spaceAfter=8,
            leading=20
        ))
        
        return styles
    
    def _parse_markdown_to_paragraphs(self, markdown_text: str, with_graph: bool = False) -> List:
        """Parse markdown text and return list of Paragraph objects."""
        elements = []
        lines = markdown_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if it's a bullet point
            is_bullet = line.startswith('- ') or line.startswith('* ')
            if is_bullet:
                line = line[2:].strip()
            
            # Apply basic markdown formatting to HTML
            formatted_text = self._markdown_to_html(line)
            
            # Create paragraph with appropriate style
            style = self.styles['SlideBullet'] if is_bullet else self.styles['SlideBody']
            
            # Add bullet symbol if needed
            if is_bullet:
                formatted_text = f'• {formatted_text}'
            
            try:
                p = Paragraph(formatted_text, style)
                elements.append(p)
            except Exception as e:
                # Fallback to plain text if formatting fails
                p = Paragraph(line, style)
                elements.append(p)
        
        return elements
    
    def _markdown_to_html(self, text: str) -> str:
        """Convert basic markdown to HTML for reportlab."""
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # Code (monospace)
        text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#6F42C1">\1</font>', text)
        
        return text
    
    def _decode_base64_image(self, base64_string: str) -> BytesIO:
        """Decode base64 image string (with or without data URI prefix)."""
        # Remove data URI prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',', 1)[1]
        
        image_data = base64.b64decode(base64_string)
        return BytesIO(image_data)
    
    def generate_pdf(
        self,
        deck_title: str,
        deck_description: Optional[str],
        slides: List[dict]
    ) -> BytesIO:
        """
        Generate a complete PDF document.
        
        Args:
            deck_title: Title of the deck
            deck_description: Optional description
            slides: List of slide dictionaries with 'title', 'content', 'graph_image' keys
        
        Returns:
            BytesIO object containing the PDF file
        """
        pdf_buffer = BytesIO()
        
        # Create document with landscape orientation (16:9 aspect ratio)
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        story = []
        
        # Title slide
        story.append(Spacer(1, 1.5*inch))
        story.append(Paragraph(deck_title, self.styles['TitleMain']))
        if deck_description:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(deck_description, self.styles['TitleSub']))
        story.append(PageBreak())
        
        # Content slides
        for slide_data in slides:
            # Add slide title
            title = slide_data.get('title', 'Untitled')
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(title, self.styles['SlideTitle']))
            story.append(Spacer(1, 0.2*inch))
            
            # Get content
            content = slide_data.get('content', '')
            graph_image = slide_data.get('graph_image')
            
            # Parse content to paragraphs
            content_elements = self._parse_markdown_to_paragraphs(
                content, 
                with_graph=bool(graph_image)
            )
            
            # Add content
            for element in content_elements:
                story.append(element)
            
            # Add image if present
            if graph_image:
                try:
                    story.append(Spacer(1, 0.2*inch))
                    image_data = self._decode_base64_image(graph_image)
                    
                    # Create Image object with appropriate sizing
                    img = Image(image_data)
                    
                    # Scale image to fit (max 6 inches wide, 3 inches tall)
                    max_width = 6 * inch
                    max_height = 3 * inch
                    
                    # Calculate aspect ratio
                    aspect = img.imageWidth / img.imageHeight
                    
                    if img.imageWidth > max_width:
                        img.drawWidth = max_width
                        img.drawHeight = max_width / aspect
                    
                    if img.drawHeight > max_height:
                        img.drawHeight = max_height
                        img.drawWidth = max_height * aspect
                    
                    story.append(img)
                except Exception as e:
                    print(f"Warning: Failed to add image to PDF slide: {e}")
            
            story.append(PageBreak())
        
        # Build PDF with custom page template
        doc.build(story, onFirstPage=SlidePage(self.theme), onLaterPages=SlidePage(self.theme))
        
        pdf_buffer.seek(0)
        return pdf_buffer


def export_to_pdf(
    deck_title: str,
    deck_description: Optional[str],
    slides: List[dict],
    theme: str = "professional"
) -> BytesIO:
    """
    Main function to export a slide deck to PDF format.
    
    Args:
        deck_title: Title of the presentation
        deck_description: Optional subtitle/description
        slides: List of slide dictionaries
        theme: Theme name (professional, modern, colorful, dark, minimalist)
    
    Returns:
        BytesIO containing the PDF file
    """
    service = PDFExportService(theme_name=theme)
    return service.generate_pdf(deck_title, deck_description, slides)
