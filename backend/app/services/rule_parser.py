import re
import fitz  # PyMuPDF


class RuleParser:
    def extract_references(self, text):
        import re

        refs = []

        # Match:
        # 23.783, 23.787
        cs_refs = re.findall(r'23\.(\d+)', text)

        # Match:
        # VLA.783, VLA.787
        vla_refs = re.findall(r'VLA\.(\d+)', text)

        # Convert to uniform format
        refs.extend([f"23.{r}" for r in cs_refs])
        refs.extend([f"VLA.{r}" for r in vla_refs])

        return list(set(refs))
    def extract_sections(self, text):
        sections = {}

        matches = re.findall(
            r'\(([a-z])\)\s*(.*?)(?=\([a-z]\)|$)',
            text,
            re.S
        )

        for label, content in matches:
            sections[label] = self.clean_text(content)

        return sections
    def clean_text(self, text):
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    def remove_toc(self, text):

        lines = text.split("\n")
        clean_lines = []
        toc_detected = True

        for line in lines:

            # TOC pattern → dots + numbers
            if re.search(r'\.{3,}\s*\d+', line):
                continue

            # Stop skipping once real rule starts
            if re.search(r'CS\s+23\.\d+\s*\(', line):
                toc_detected = False

            if not toc_detected:
                clean_lines.append(line)

        return "\n".join(clean_lines)
    def extract_text_from_pdf(self, pdf_path):
        import fitz

        doc = fitz.open(pdf_path)
        full_text = ""

        for page in doc:
            blocks = page.get_text("blocks")  # 🔥 structured extraction

            for block in blocks:
                text = block[4]

                # Skip tiny garbage blocks
                if len(text.strip()) < 5:
                    continue

                full_text += text + "\n"

        return full_text

    def parse(self, text, regulation_id=1):
        current_subpart = "General"
        import re

        # ---------------- CLEANING ----------------
        text = re.sub(r'http\S+', '', text)

        # Normalize line breaks
        text = text.replace("\r", "\n")

        lines = text.split("\n")

        rules = []

        # ✅ Strict rule pattern
        rule_pattern = re.compile(r'^(CS|AMC\d+|GM\d+)\s+23\.(\d+)\s+(.*)')

        current_rule = None
        current_text = []

        for line in lines:

            line = line.strip()

            # ---------------- SKIP JUNK ----------------
            if not line or len(line) < 3:
                continue

            # ❌ Table of contents (dots + page numbers)
            if re.search(r'\.{3,}', line):
                continue

            # ❌ Headers / footers
            if any(x in line for x in [
                "AMC & GM to CS-23",
                "CS-23 — Amendment",
                "Table of Contents",
                "ED Decision",
                "Annex to",
                "Preamble"
            ]):
                continue

            # ❌ Subparts / sections
            if "SUBPART" in line:
                # ✅ Detect SUBPART
                subpart_match = re.match(r'SUBPART\s+([A-Z])\s*[-–]?\s*(.*)', line)

                if subpart_match:
                    current_subpart = f"Subpart {subpart_match.group(1)}"
                    continue

                # Skip appendix
            if "Appendix" in line:
                continue

            # ❌ Amendment history lines
            if re.search(r'Created|Deleted|Amended|NPA', line):
                continue

            # ❌ Range rules (fake)
            if re.search(r'CS\s+23\.\d+\s+through\s+CS\s+23\.\d+', line):
                continue

            # ---------------- RULE DETECTION ----------------
            match = rule_pattern.match(line)

            if match:

                # Save previous rule
                if current_rule and current_text:
                    full_text = "\n".join(current_text)

                    # 🔥 NEW: extract subsections
                    #full_text = "\n".join(current_text)

                    # 🔥 EXTRACT REFERENCES
                    references = self.extract_references(full_text)

                    if current_rule["type"] == "CS":
                        sections = self.extract_sections(full_text)

                        if sections:
                            current_rule["text"] = sections
                        else:
                            current_rule["text"] = full_text.strip()

                    else:
                        # ✅ AMC & GM RAW TEXT (NO PARSING)
                        current_rule["text"] = full_text.strip()

                    # 🔥 STORE REFERENCES
                    current_rule["references"] = references

                    rules.append(current_rule)

                rule_type = match.group(1)
                rule_number = match.group(2)

                # ✅ Clean title (remove trailing dots/pages)
                title = re.sub(r'\.{3,}.*', '', match.group(3)).strip()

                current_rule = {
                    "rule_number": rule_number,
                    "type": rule_type,
                    "title": self.clean_text(f"{rule_type} 23.{rule_number} {title}"),
                    "text": "",
                    "subpart": current_subpart,   # ✅ ADD THIS
                    "regulation_id": regulation_id
                }

                current_text = []
                continue

            # ---------------- TEXT ACCUMULATION ----------------
            if current_rule:
                current_text.append(line)

        # Save last rule
        if current_rule and current_text:
            full_text = "\n".join(current_text)

            # 🔥 NEW: extract subsections
            if current_rule["type"] == "CS":
                sections = self.extract_sections(full_text)

                if sections:
                    current_rule["text"] = sections
                else:
                    current_rule["text"] = full_text.strip()
            else:
                # ✅ AMC & GM should stay RAW TEXT
                current_rule["text"] = full_text.strip()

            rules.append(current_rule)

        return rules