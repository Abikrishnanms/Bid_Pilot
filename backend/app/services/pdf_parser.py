import pdfplumber
import os

class PDFParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extracts raw text from a PDF file using pdfplumber.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Tender PDF not found: {file_path}")
            
        full_text = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
            return "\n".join(full_text)
        except Exception as e:
            raise RuntimeError(f"Error parsing PDF {file_path}: {str(e)}")
