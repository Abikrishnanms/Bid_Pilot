import logging
from ..services.pdf_parser import PDFParser
from ..services.llm_provider import get_llm_provider
from ..schemas.tender import ExtractedRequirements

logger = logging.getLogger(__name__)

class ExtractionAgent:
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.llm_provider = get_llm_provider()

    def process_text(self, raw_text: str) -> ExtractedRequirements:
        """
        Use LLM to extract structured data from raw tender text.
        """
        prompt = (
            "Analyze the following tender document or specification and extract the requirements according "
            "to the specified schema. If a field is not found, leave it empty or provide a logical default."
        )
        
        try:
            structured_data = self.llm_provider.extract_structured_data(
                text=raw_text,
                schema=ExtractedRequirements,
                prompt=prompt
            )
            logger.info("Successfully extracted structured requirements.")
            return structured_data
        except Exception as e:
            logger.error(f"Failed to extract structured data: {str(e)}")
            raise

    def process_tender(self, file_path: str) -> ExtractedRequirements:
        """
        Main pipeline to parse PDF and extract structured requirements.
        """
        logger.info(f"Starting extraction for {file_path}")
        raw_text = self.pdf_parser.extract_text(file_path)
        logger.info(f"Extracted {len(raw_text)} characters of text from PDF.")
        return self.process_text(raw_text)
