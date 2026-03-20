"""
Document Generation Service
Handles PDF generation and document serving for regulatory updates
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class DocumentService:
    """Service for generating and managing PDF documents"""
    
    def __init__(self):
        self.pdf_dir = Path(tempfile.gettempdir()) / "regulatory_pdfs"
        self.pdf_dir.mkdir(exist_ok=True)
        self.has_reportlab = HAS_REPORTLAB
    
    def generate_pdf(
        self, 
        update_id: int,
        title: str,
        authority: str,
        published_date: datetime,
        category: str,
        full_text: str,
        short_summary: str,
        source_link: str
    ) -> Optional[str]:
        """
        Generate a PDF document from update information
        Returns: Path to generated PDF file or None if generation fails
        """
        
        if not self.has_reportlab:
            print("[PDF] ReportLab not installed - PDF generation disabled")
            return None
        
        try:
            # Create unique filename
            filename = f"update_{update_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = self.pdf_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            
            # Container for PDF elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=12,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#2e5c8a'),
                spaceAfter=8,
                spaceBefore=8,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=6,
            )
            
            # Add title
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Add metadata table
            metadata = [
                ['Authority:', authority],
                ['Category:', category],
                ['Published Date:', published_date.strftime('%Y-%m-%d %H:%M:%S') if published_date else 'N/A'],
                ['Source URL:', source_link[:60] + '...' if len(source_link) > 60 else source_link],
            ]
            
            metadata_table = Table(metadata, colWidths=[2.0*inch, 4.0*inch])
            metadata_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f0f7')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ]))
            
            elements.append(metadata_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Add summary
            elements.append(Paragraph('Summary', heading_style))
            if short_summary:
                elements.append(Paragraph(short_summary, normal_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Add full content
            if full_text:
                elements.append(Paragraph('Full Content', heading_style))
                # Split long text into paragraphs
                paragraphs = full_text.split('\n')
                for para in paragraphs:
                    if para.strip():
                        elements.append(Paragraph(para.strip(), normal_style))
                elements.append(Spacer(1, 0.1*inch))
            
            # Add footer
            elements.append(Spacer(1, 0.3*inch))
            footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Update ID: {update_id}"
            elements.append(Paragraph(footer_text, styles['Normal']))
            
            # Build PDF
            doc.build(elements)
            
            print(f"[PDF] Generated PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"[PDF] Error generating PDF: {str(e)}")
            return None
    
    def get_pdf_path(self, update_id: int) -> Optional[str]:
        """Get the path to a PDF file for an update"""
        # Look for PDF files matching the update_id
        pattern = f"update_{update_id}_*.pdf"
        matches = list(self.pdf_dir.glob(pattern))
        
        if matches:
            # Return the most recent one
            return str(sorted(matches, key=os.path.getmtime, reverse=True)[0])
        
        return None
    
    def cleanup_old_pdfs(self, days_old: int = 7) -> int:
        """Clean up PDF files older than specified days. Returns count deleted."""
        import time
        
        if not self.pdf_dir.exists():
            return 0
        
        cutoff_time = time.time() - (days_old * 86400)
        deleted_count = 0
        
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            if os.path.getmtime(pdf_file) < cutoff_time:
                try:
                    os.remove(pdf_file)
                    deleted_count += 1
                except Exception as e:
                    print(f"[PDF] Error deleting {pdf_file}: {str(e)}")
        
        return deleted_count


# Global instance
document_service = DocumentService()
