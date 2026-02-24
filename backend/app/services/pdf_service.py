"""
PDF Extraction Service for Guideline Documents
Extracts text from PDF files for regulatory guideline repositories
"""

import requests
from typing import Optional, Tuple
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class PDFService:
    """Service for extracting text from regulatory PDF documents"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    def extract_text_from_url(self, pdf_url: str) -> Optional[str]:
        """
        Download PDF from URL and extract text.
        
        Args:
            pdf_url: URL to PDF file
            
        Returns:
            Extracted text or None if extraction fails
        """
        try:
            print(f"[PDF SERVICE] Downloading PDF from: {pdf_url[:80]}")
            
            # Download PDF
            response = requests.get(pdf_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            if not response.content:
                print(f"[PDF SERVICE] Empty PDF content from {pdf_url}")
                return None
            
            # Extract text using PyPDF2
            try:
                import PyPDF2
                pdf_file = BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                if not pdf_reader.pages:
                    print(f"[PDF SERVICE] No pages in PDF: {pdf_url}")
                    return None
                
                # Extract text from all pages (limit to first 50 pages for large documents)
                text_parts = []
                max_pages = min(len(pdf_reader.pages), 50)
                
                for page_num in range(max_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        print(f"[PDF SERVICE] Error extracting page {page_num}: {e}")
                        continue
                
                extracted_text = "\n".join(text_parts)
                
                if not extracted_text.strip():
                    print(f"[PDF SERVICE] No text extracted from PDF: {pdf_url}")
                    return None
                
                print(f"[PDF SERVICE] Successfully extracted {len(extracted_text)} chars from PDF")
                return extracted_text
                
            except ImportError:
                # Fallback: Use pdfplumber if available
                try:
                    import pdfplumber
                    pdf_file = BytesIO(response.content)
                    
                    with pdfplumber.open(pdf_file) as pdf:
                        if not pdf.pages:
                            print(f"[PDF SERVICE] No pages in PDF: {pdf_url}")
                            return None
                        
                        text_parts = []
                        max_pages = min(len(pdf.pages), 50)
                        
                        for page_num in range(max_pages):
                            try:
                                page = pdf.pages[page_num]
                                text = page.extract_text()
                                if text:
                                    text_parts.append(text)
                            except Exception as e:
                                print(f"[PDF SERVICE] Error extracting page {page_num}: {e}")
                                continue
                        
                        extracted_text = "\n".join(text_parts)
                        
                        if not extracted_text.strip():
                            print(f"[PDF SERVICE] No text extracted from PDF: {pdf_url}")
                            return None
                        
                        print(f"[PDF SERVICE] Successfully extracted {len(extracted_text)} chars from PDF")
                        return extracted_text
                        
                except ImportError:
                    print(f"[PDF SERVICE] Neither PyPDF2 nor pdfplumber available - using text fallback")
                    # Fallback: Return generic message about manual retrieval
                    return "[PDF text extraction not available - please download from source link]"
        
        except requests.exceptions.RequestException as e:
            print(f"[PDF SERVICE] Error downloading PDF from {pdf_url}: {e}")
            return None
        except Exception as e:
            print(f"[PDF SERVICE] Unexpected error processing PDF: {e}")
            return None
    
    def create_text_summary(self, full_text: str, max_chars: int = 500) -> str:
        """
        Create a summary from extracted PDF text.
        
        Args:
            full_text: Full extracted text
            max_chars: Maximum characters for summary
            
        Returns:
            Text summary
        """
        if not full_text:
            return ""
        
        # Clean up text: remove excessive whitespace
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        text = ' '.join(lines)
        
        # Return first max_chars characters, breaking at word boundary
        if len(text) <= max_chars:
            return text
        
        summary = text[:max_chars]
        # Find last space to break at word boundary
        last_space = summary.rfind(' ')
        if last_space > 0:
            summary = summary[:last_space]
        
        return summary + "..."


# Global service instance
pdf_service = PDFService()
