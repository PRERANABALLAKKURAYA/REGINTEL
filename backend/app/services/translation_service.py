"""
Translation service for non-English content (PMDA, NMPA, etc.)
Automatically translates titles and summaries to English.
"""
import logging
from typing import Optional

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    GoogleTranslator = None

logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self):
        self.translator = None
        if TRANSLATOR_AVAILABLE:
            self.translator = GoogleTranslator
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the text"""
        if not text or len(text) < 2:
            return 'en'
        
        try:
            # For deep_translator, we'll assume Japanese or detect by trying to translate
            # If it translates to itself, it's probably already English
            if not self.translator:
                return 'en'
            
            # Simple heuristic: check if text contains Japanese characters
            for char in text:
                if ord(char) > 0x3040:  # Japanese character range
                    return 'ja'
            
            return 'en'
        except Exception as e:
            logger.debug(f"Error detecting language: {e}")
            return 'en'
    
    def translate_to_english(self, text: str, source_lang: Optional[str] = None) -> str:
        """
        Translate text to English if it's not already in English.
        Returns original text if translation fails or not needed.
        """
        if not text or len(text) < 2:
            return text
        
        try:
            if not self.translator:
                return text
            
            # Detect language if not provided
            if not source_lang:
                source_lang = self.detect_language(text)
            
            # Already in English
            if source_lang == 'en':
                return text
            
            # Translate to English
            logger.info(f"[TRANSLATION] Translating from {source_lang} to English: {text[:50]}...")
            translator = self.translator(source_language=source_lang, target_language='en')
            translated_text = translator.translate(text)
            logger.info(f"[TRANSLATION] Result: {translated_text[:50]}...")
            return translated_text
        
        except Exception as e:
            logger.warning(f"Translation failed for text '{text[:50]}...': {e}")
            return text
    
    def translate_update(self, title: str, summary: Optional[str] = None, authority: str = "Unknown") -> tuple[str, Optional[str]]:
        """
        Translate both title and summary, detecting language automatically.
        Returns tuple of (translated_title, translated_summary)
        """
        # Translate title
        translated_title = self.translate_to_english(title)
        
        # Translate summary if provided
        translated_summary = None
        if summary:
            translated_summary = self.translate_to_english(summary)
        
        if translated_title != title or (summary and translated_summary != summary):
            logger.info(f"[TRANSLATION] {authority} - Title translated: {title != translated_title}, Summary translated: {bool(summary and translated_summary != summary)}")
        
        return translated_title, translated_summary

# Global instance
translation_service = TranslationService()

def translate_update(title: str, summary: Optional[str] = None, authority: str = "Unknown") -> tuple[str, Optional[str]]:
    """Convenience function to translate updates"""
    return translation_service.translate_update(title, summary, authority)
