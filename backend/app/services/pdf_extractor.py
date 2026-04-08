import pdfplumber
import re
import pymupdf4llm

class PDFExtractor:

    def extract_text(self, file_path):
        import pdfplumber
        import re

        full_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:

                # ✅ Extract full page directly (NO COLUMN SPLIT)
                text = page.extract_text() or ""

                text = self._clean_page(text)

                # Fix broken words
                text = re.sub(r'\n(?=[a-z])', ' ', text)

                full_text += text + "\n"

        return full_text
    
    def _clean_page(self, text):
        text = re.sub(r"Easy Access Rules.*", "", text)
        text = re.sub(r"Page\s+\d+.*", "", text)

        # 🔥 Remove EASA noise
        text = re.sub(r"Amendment\s+\d+\s+CS-23\s+BOOK\s+\d+", "", text)

        return text.strip()
    
    def remove_toc_lines(self,text):
        cleaned_lines = []

        for line in text.split("\n"):
            # Remove dotted TOC entries ending with page numbers
            if re.search(r"\.{3,}\s*\d+$", line):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)
    
    # def extract_text(self, file_path):
    #     text = pymupdf4llm.to_markdown(file_path)

    #     # 🔥 Normalize markdown → plain text
    #     text = self._normalize_markdown(text)

    #     return text

    def _normalize_markdown(self, text):
        import re

        # Remove markdown headers (#, ##, ###)
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r'(\*\*|\*)', '', text)

        # Remove excessive blank lines
        text = re.sub(r'\n{2,}', '\n', text)

        return text.strip()