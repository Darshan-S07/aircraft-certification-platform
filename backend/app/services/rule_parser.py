import re
import json
from typing import List, Dict


class RuleParser:

    # ================= PDF TEXT EXTRACTION =================
    def extract_text_from_pdf(self, file_path: str) -> str:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        text = ""

        for page in reader.pages:
            text += page.extract_text() + "\n"

        return text

    # ================= REMOVE TOC =================
    def remove_toc(self, text: str) -> str:
        # Simple cleanup — you can improve later
        return text

    # ================= MAIN PARSER =================
    def parse(self, text: str) -> List[Dict]:

        rules = []
        current = None

        lines = text.split("\n")

        for line in lines:
            line = line.strip()

            # 🔹 Detect CS rule
            cs_match = re.match(r'^CS\s*23\.(\d+)', line)

            # 🔹 Detect AMC
            amc_match = re.match(r'^(AMC\d*)\s*23\.(\d+)', line)

            # 🔹 Detect GM
            gm_match = re.match(r'^(GM\d*)\s*23\.(\d+)', line)

            if cs_match:
                if current:
                    rules.append(current)

                current = {
                    "rule_number": cs_match.group(1),
                    "type": "CS",
                    "title": line,
                    "text": "",
                    "references": [],
                    "subpart": None
                }

            elif amc_match:
                if current:
                    rules.append(current)

                current = {
                    "rule_number": amc_match.group(2),
                    "type": amc_match.group(1),
                    "title": line,
                    "text": "",
                    "references": [],
                    "subpart": None
                }

            elif gm_match:
                if current:
                    rules.append(current)

                current = {
                    "rule_number": gm_match.group(2),
                    "type": gm_match.group(1),
                    "title": line,
                    "text": "",
                    "references": [],
                    "subpart": None
                }

            elif current:
                current["text"] += line + "\n"

        if current:
            rules.append(current)

        # 🔥 AFTER PARSING → EXTRACT REFERENCES FOR AMC ONLY
        for rule in rules:
            if rule["type"].startswith("AMC"):
                rule["references"] = self.extract_references(rule["text"])

        return rules

    # ================= 🔥 STEP 1: EXTRACT REFERENCES =================
    def extract_references(self, text: str) -> List[str]:

        refs = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()

            match = re.match(r'(23\.\d+|VLA\.\d+)', line)
            if not match:
                continue

            base = match.group(1)

            parts = re.findall(r'\([a-z0-9]+\)', line)

            if parts:
                current = ""
                for p in parts:
                    current += p
                    refs.append(base + current)
            else:
                refs.append(base)

        return list(set(refs))


# ================= 🔥 STEP 2: SPLIT REFERENCE =================
def split_reference(ref: str):
    match = re.match(r'(23\.\d+|VLA\.\d+)', ref)
    if not match:
        return None, None

    base = match.group(1)
    subsection = ref.replace(base, "")

    return base, subsection


# ================= 🔥 STEP 3: EXTRACT SUBSECTION =================
def extract_subsection(text: str, subsection: str):

    if not text or not text.startswith("{"):
        return text

    data = json.loads(text)

    keys = re.findall(r'\(([a-z0-9]+)\)', subsection)

    current = data

    try:
        for k in keys:
            current = current[k]
        return current
    except:
        return None


# ================= 🔥 STEP 4: FETCH RULE WITH SUBSECTION =================
def fetch_reference_rule(ref: str):

    import sqlite3

    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    base, subsection = split_reference(ref)

    if not base:
        return None

    rule_number = base.replace("23.", "").replace("VLA.", "")

    cursor.execute("""
        SELECT title, text FROM rules
        WHERE rule_number = ? AND type = 'CS'
    """, (rule_number,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    title, text = row

    # 🔥 Extract subsection if exists
    if subsection:
        extracted = extract_subsection(text, subsection)

        if extracted:
            return title + f" {subsection}", extracted

    return title, text