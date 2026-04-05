import re
import fitz  # PyMuPDF


class RuleParser:
    def filter_subsections(self, text, subs):
        import json
        import re

        # CASE 1: JSON structured (BEST case)
        if text.startswith("{"):
            data = json.loads(text)

            if not subs:
                return data

            filtered = {}
            for sub in subs:
                key = sub.replace("(", "").replace(")", "")
                if key in data:
                    filtered[key] = data[key]

            return filtered

        # CASE 2: RAW TEXT → extract manually
        sections = re.findall(r'\(([a-z])\)(.*?)(?=\([a-z]\)|$)', text, re.S)

        if not sections:
            return text

        if not subs:
            return dict(sections)

        filtered = {}

        for label, content in sections:
            if label in subs:
                filtered[label] = content.strip()

        return filtered
    def split_rules(self,text):
        import re

        # Split ONLY when rule starts at beginning
        rule_splits = re.split(r'\n(?=(CS|AMC\d+|GM\d+)?\s*23\.\d+)', text)

        rules = []
        current = ""

        for part in rule_splits:
            if re.match(r'^(CS|AMC\d+|GM\d+)?\s*23\.\d+', part):
                if current:
                    rules.append(current.strip())
                current = part
            else:
                current += " " + part

        if current:
            rules.append(current.strip())

        return rules
    def extract_references(self,text):
        import re

        pattern = r'23\.(\d+)((?:\([a-z0-9]+\))*)'
        matches = re.findall(pattern, text)

        refs = []

        for rule, subs in matches:
            subs_list = re.findall(r'\(([a-z0-9]+)\)', subs)
            refs.append({
                "rule": f"23.{rule}",
                "subs": subs_list
            })

        return refs
    def extract_sections(self, text):
        import re

        sections = {}

        # Match (a), (b), (c)(1), (c)(2)
        pattern = r'\(([a-z])\)((?:\(\d+\))?)\s*(.*?)(?=\([a-z]\)|$)'

        matches = re.findall(pattern, text, re.S)

        for main, sub, content in matches:
            key = main + sub.replace("(", "").replace(")", "")
            sections[key] = self.clean_text(content)

        return sections
    def clean_text(self,text):
        import re

        lines = text.split("\n")
        clean_lines = []

        for line in lines:
            line = line.strip()

            # ❌ Remove page numbers only
            if re.match(r'^Page \d+ of \d+', line):
                continue

            # ❌ Remove empty lines
            if len(line) == 0:
                continue

            clean_lines.append(line)

        return "\n".join(clean_lines)
    def remove_toc(self, text):

        raw_lines = text.split("\n")

        lines = []
        buffer = ""

        for line in raw_lines:
            line = line.strip()

            if not line:
                continue

            # If line starts with reference → attach to previous
            if re.match(r'^(23\.\d+|VLA\.\d+)', line):
                buffer += " " + line
            else:
                if buffer:
                    lines.append(buffer)
                buffer = line

        if buffer:
            lines.append(buffer)
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
            blocks = page.get_text("blocks")

            # Sort blocks top → bottom
            blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

            page_width = page.rect.width
            mid_x = page_width / 2

            left_col = []
            right_col = []

            for b in blocks:
                x0, y0, x1, y1, text, *_ = b

                if len(text.strip()) < 5:
                    continue

                # Split into columns
                if x0 < mid_x:
                    left_col.append((y0, text))
                else:
                    right_col.append((y0, text))

            # Sort each column top → bottom
            left_col = sorted(left_col, key=lambda x: x[0])
            right_col = sorted(right_col, key=lambda x: x[0])

            # Merge properly: LEFT first, then RIGHT
            for _, t in left_col:
                full_text += t + "\n"

            for _, t in right_col:
                full_text += t + "\n"

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
        rule_pattern = re.compile(r'^(CS|AMC\d+|GM\d+)\s+23\.(\d{2,4})\b(.*)')

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
            # ❌ Remove page numbers
            if re.match(r'Page \d+ of \d+', line):
                continue

            # ❌ Remove amendment lines
            if "Amdt" in line and not current_rule:
                continue

            # ❌ Remove section headings
            # if line.isupper() and len(line) < 30:
            #     continue
              # ❌ Skip pure reference lines
            # ❌ Skip reference lines ONLY for CS (not AMC)
            if current_rule and current_rule["type"] == "CS":
                if re.match(r'^(23\.\d+)', line):
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
#                     references = self.extract_references(full_text)
# current_rule["references"] = references
                    # 🔥 ADD THIS LINE (MISSING)
                    references = self.extract_references(full_text)
                    current_rule["references"] = references

                    if current_rule["type"] == "CS":
                        sections = self.extract_sections(full_text)

                        if sections:
                            current_rule["text"] = sections
                        else:
                            current_rule["text"] = full_text.strip()
                    else:
                        current_rule["text"] = full_text.strip()

                    rules.append(current_rule)

                rule_type = match.group(1) if match.group(1) else "CS"
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
                if current_text and not current_text[-1].endswith((".", ":", ")")):
                    current_text[-1] += " " + line
                else:
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
                current_rule["text"] = self.clean_text(full_text)

            rules.append(current_rule)
        for r in rules[:20]:
            print(r['rule_number'])

        return rules