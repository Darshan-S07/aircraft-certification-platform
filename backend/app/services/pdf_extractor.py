import pdfplumber
import re


class PDFExtractor:

    def extract_text(self, file_path):
        full_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True)

                if not text:
                    continue

                # Remove header/footer noise
                text = self._clean_page(text)

                full_text += text + "\n"
        print(full_text[:50000])
        return full_text

    def _clean_page(self, text):
        # Remove common EASA header/footer patterns
        text = re.sub(r"Easy Access Rules.*", "", text)
        text = re.sub(r"Page\s+\d+.*", "", text)

        return text
    
    def remove_toc_lines(self,text):
        cleaned_lines = []

        for line in text.split("\n"):
            # Remove dotted TOC entries ending with page numbers
            if re.search(r"\.{3,}\s*\d+$", line):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)