import re
import fitz  # PyMuPDF


class RuleParser:
    def __init__(self):
        self.cs_master_rules = {}
    def split_into_rule_blocks(self, text):
        import re

        # 🔥 Find ALL rule start positions
        pattern = r'(CS|AMC\d+|GM\d+)\s+23\.\d{2,4}'

        matches = list(re.finditer(pattern, text))

        blocks = []

        for i in range(len(matches)):
            start = matches[i].start()

            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)

            block = text[start:end].strip()
            blocks.append(block)

        return blocks
    def remove_table_noise(self, text):
        import re

        lines = text.split("\n")
        clean = []

        for line in lines:
            if re.search(r'\d+\s+to\s+\d+', line):
                continue
            if re.search(r'\.{3,}', line):
                continue
            if re.search(r'\(\d+\)', line) and len(line.split()) < 5:
                continue

            clean.append(line)

        return "\n".join(clean)
    def is_rule_header(self, line):
        import re

        return bool(re.match(r'^(CS|AMC\d+|GM\d+)\s+23\.\d+\s+[A-Za-z]',line.strip()))
    def normalize_text(self, text):
        import re

        # ✅ Join broken lines inside sentences
        text = re.sub(r'\n(?=[a-z])', ' ', text)

        # ✅ Fix cases like:
        # (a)\nSome text → (a) Some text
        text = re.sub(r'\(([a-z])\)\s*\n\s*', r'(\1) ', text)

        # ✅ Remove extra newlines
        text = re.sub(r'\n+', '\n', text)

        return text.strip()
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
    def extract_references(self, text):
        import re

        refs = []

        pattern = r'(23\.\d+)((?:\([a-z0-9]+\))*)'
        matches = re.findall(pattern, text)

        for base, subs in matches:
            sub_parts = re.findall(r'\(([a-z0-9]+)\)', subs)

            if sub_parts:
                for sub in sub_parts:
                    refs.append(f"{base}({sub})")
            else:
                refs.append(base)

        return list(set(refs))
    def extract_sections(self, text):
        import re

        pattern = r'\(([a-z])\)\s*(.*?)((?=\([a-z]\))|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        clauses = {}

        for key, content, _ in matches:
            clauses[key] = content.strip()

        return clauses
    def clean_text(self,text):
        import re
        text = re.sub(r'Amendment\s+\d+\s+CS-23\s+BOOK\s+\d+', '', text)
        text = re.sub(r'\b(or|and)\b\s*$', '', text)
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
        # import fitz

        # doc = fitz.open(pdf_path)
        # full_text = ""

        # for page in doc:
        #     blocks = page.get_text("blocks")

        #     # Sort blocks top → bottom
        #     blocks = sorted(blocks, key=lambda b: (b[1], b[0]))

        #     page_width = page.rect.width
        #     mid_x = page_width / 2

        #     left_col = []
        #     right_col = []

        #     for b in blocks:
        #         x0, y0, x1, y1, text, *_ = b

        #         if len(text.strip()) < 5:
        #             continue

        #         # Split into columns
        #         if x0 < mid_x:
        #             left_col.append((y0, text))
        #         else:
        #             right_col.append((y0, text))

        #     # Sort each column top → bottom
        #     left_col = sorted(left_col, key=lambda x: x[0])
        #     right_col = sorted(right_col, key=lambda x: x[0])

        #     # Merge properly: LEFT first, then RIGHT
        #     # Merge both columns and sort by vertical position
        #     merged_blocks = []

        #     for y, text in left_col:
        #         merged_blocks.append((y, text))

        #     for y, text in right_col:
        #         merged_blocks.append((y, text))

        #     # Sort ALL blocks top → bottom
        #     merged_blocks = sorted(merged_blocks, key=lambda x: x[0])

        #     # Now reconstruct text in reading order
        #     for _, t in merged_blocks:
        #         full_text += t + "\n"
        import pymupdf4llm

        text = pymupdf4llm.to_markdown(pdf_path)
        return text
        # return full_text

    def parse(self, text, regulation_id=1):
        import re

        text = self.normalize_text(text)
        text = self.remove_table_noise(text)

        # ---------------- CLEANING ----------------
        text = re.sub(r'http\S+', '', text)
        text = text.replace("\r", "\n")

        # 🔥 NEW BLOCK-BASED PARSING
        blocks = self.split_into_rule_blocks(text)

        rules = []

        rule_pattern = re.compile(
            r'^(CS|AMC\d+|GM\d+)\s+23\.(\d{2,4})\b\s*(.*)',
            re.IGNORECASE
        )

        for block in blocks:

            block = block.strip()
            if len(block) < 10:
                continue

            match = rule_pattern.match(block)

            if not match:
                continue

            rule_type = match.group(1)
            rule_number = match.group(2)

            # Title = first line only
            first_line = block.split("\n")[0]
            title = first_line.replace(match.group(0), "").strip()

            full_text = block
            full_text = re.sub(r'Subpart\s+[A-Z].*', '', full_text)
            current_rule = {
                "rule_number": rule_number,
                "type": rule_type,
                "title": self.clean_text(f"{rule_type} 23.{rule_number}"),
                "text": "",
                "subpart": "General",
                "regulation_id": regulation_id
            }

            # ✅ Extract references
            current_rule["references"] = self.extract_references(full_text)

            # ✅ Handle CS rules
            if rule_type == "CS":
                sections = self.extract_sections(full_text)

                if sections:
                    current_rule["text"] = sections
                else:
                    current_rule["text"] = self.clean_text(full_text)

                # ✅ Store CS master
                rule_id = f"23.{rule_number}"
                self.cs_master_rules[rule_id] = current_rule

            else:
                current_rule["text"] = self.clean_text(full_text)

            rules.append(current_rule)

        # 🔥 DEBUG (optional)
        for r in rules[:20]:
            print(r['rule_number'])

        return rules