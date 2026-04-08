import os
from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.regulation import Regulation
from app.models.rule import Rule
from app.services.rule_parser import RuleParser
import sqlite3
import json
from app.services.pdf_extractor import PDFExtractor
from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter()

UPLOAD_FOLDER = "uploaded_pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================= DB =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================= UPLOAD =================
@router.post("/upload-regulation/")
async def upload_regulation(
    name: str,
    version: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    existing = db.query(Regulation).filter(
        Regulation.name == name,
        Regulation.version == version
    ).first()

    if existing:
        regulation = existing
    else:
        regulation = Regulation(name=name, version=version)
        db.add(regulation)
        db.commit()
        db.refresh(regulation)

    extractor = PDFExtractor()
    text = extractor.extract_text(file_path)

    parser = RuleParser()
    rules_data = parser.parse(text)

    inserted_rules = set()

    for r in rules_data:
        key = (r["rule_number"], r["type"], regulation.id)

        if key in inserted_rules:
            continue
        inserted_rules.add(key)

        existing_rule = db.query(Rule).filter(
            Rule.rule_number == r["rule_number"],
            Rule.type == r["type"],
            Rule.regulation_id == regulation.id
        ).first()

        if existing_rule:
            continue

        text_data = json.dumps(r["text"]) if isinstance(r["text"], dict) else r["text"]

        rule_obj = Rule(
            rule_number=r["rule_number"],
            type=r["type"],
            title=r["title"],
            text=text_data,
            references=json.dumps(r.get("references", [])),
            subpart=r["subpart"],
            regulation_id=regulation.id
        )

        db.add(rule_obj)

    db.commit()
    print("🔥 TOTAL CS:", len(parser.cs_master_rules))

    for k in list(parser.cs_master_rules.keys())[:10]:
        print("CS:", k)
    return {
        "message": "Uploaded successfully",
        "rules_count": len(rules_data)
    }


# ================= FETCH RULE =================
@router.get("/rules/{rule_number}")
def get_rule(rule_number: str):

    rule_number = rule_number.replace("23.", "")

    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rule_number, type, title, text
        FROM rules
        WHERE rule_number = ?
    """, (rule_number,))

    rows = cursor.fetchall()
    conn.close()

    cs, amc, gm = None, [], []

    for r in rows:
        data = {
            "rule_number": r[0],
            "type": r[1],
            "title": r[2],
            "text": json.loads(r[3]) if r[3].startswith("{") else r[3]
        }

        if r[1] == "CS":
            cs = data
        elif r[1].startswith("AMC"):
            amc.append(data)
        elif r[1].startswith("GM"):
            gm.append(data)

    return {"cs": cs, "amc": amc, "gm": gm}


# ================= RULE LIST =================
@router.get("/rules-list")
def get_rules_list(subpart: str = None):

    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    if subpart:
        cursor.execute("""
            SELECT DISTINCT rule_number, title
            FROM rules
            WHERE type = 'CS' AND subpart = ?
        """, (subpart,))
    else:
        cursor.execute("""
            SELECT DISTINCT rule_number, title
            FROM rules
            WHERE type = 'CS'
        """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {"label": f"CS {r[0]} - {r[1]}", "value": r[0]}
        for r in rows
    ]

def filter_subsections(text, subs):
    if not text.startswith("{"):
        return text

    data = json.loads(text)

    if not subs:
        return data

    filtered = {}

    for sub in subs:
        key = sub.replace("(", "").replace(")", "")
        if key in data:
            filtered[key] = data[key]

    return filtered
# ================= FETCH REFERENCE =================
def fetch_reference_rule(ref):
    import sqlite3

    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    ref = ref.strip()

    # Handle CS reference
    if ref.startswith("23."):
        ref_num = ref.replace("23.", "")

    elif ref.startswith("VLA."):
        ref_num = ref.replace("VLA.", "")

    else:
        return None

    cursor.execute("""
        SELECT title, text FROM rules
        WHERE rule_number = ? AND type = 'CS'
    """, (ref_num,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"⚠️ Reference NOT FOUND in DB: {ref}")  # DEBUG
        return None

    return row

# ================= EXPORT PDF =================
@router.get("/export/{rule_number}")
def export_rule(rule_number: str, amc: int = None):

    rule_number = rule_number.replace("23.", "")

    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT type, title, text, "references"
        FROM rules
        WHERE rule_number = ?
        ORDER BY 
            CASE 
                WHEN type = 'CS' THEN 1
                WHEN type LIKE 'AMC%' THEN 2
                WHEN type LIKE 'GM%' THEN 3
            END
    """, (rule_number,))

    rows = cursor.fetchall()
    conn.close()

    cs, amc_list, gm_list = None, [], []

    for r in rows:
        r_type, title, text, refs = r
        references = json.loads(refs) if refs else []

        entry = {
            "title": title,
            "text": text,
            "references": references
        }

        if r_type == "CS":
            cs = entry
        elif r_type.startswith("AMC"):
            amc_list.append(entry)
        elif r_type.startswith("GM"):
            gm_list.append(entry)

    file_path = f"rule_{rule_number}.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    elements = []

    def render(text):
        blocks = []
        if not text:
            return blocks

        if text.startswith("{"):
            sections = json.loads(text)
            for sec, val in sections.items():
                blocks.append(Paragraph(f"<b>({sec})</b> {val}", styles["Normal"]))
                blocks.append(Spacer(1, 8))
        else:
            for line in text.split("\n"):
                if line.strip():
                    blocks.append(Paragraph(line, styles["Normal"]))
                    blocks.append(Spacer(1, 6))

        return blocks

    # CS
    if cs:
        elements.append(Paragraph("<b>CS</b>", styles["Heading2"]))
        elements.append(Paragraph(cs["title"], styles["Heading3"]))
        elements.extend(render(cs["text"]))
        elements.append(Spacer(1, 20))

    # AMC
    if amc_list:
        elements.append(Paragraph("<b>AMC</b>", styles["Heading2"]))
        printed_refs=set()
        for index, amc_item in enumerate(amc_list, start=1):

            if amc is not None and index != amc:
                continue
            elements.append(Paragraph(amc_item["title"], styles["Heading3"]))
            elements.extend(render(amc_item["text"]))

            unique_refs = {}

            for ref in amc_item.get("references", []):

                # ✅ Case 1: ref is already structured dict
                if isinstance(ref, dict):
                    rule = ref.get("rule")
                    subs = tuple(ref.get("subs", []))

                # ✅ Case 2: ref is string → convert to structured
                elif isinstance(ref, str):
                    import re
                    match = re.match(r'(23\.\d+)((?:\([a-z0-9]+\))*)', ref)

                    if match:
                        rule = match.group(1)
                        subs = tuple(re.findall(r'\(([a-z0-9]+)\)', match.group(2)))
                    else:
                        continue

                else:
                    continue

                key = (rule, subs)
                unique_refs[key] = {
                    "rule": rule,
                    "subs": list(subs)
                }

            refs = list(unique_refs.values())
            print("References:",refs)
            from app.services.rule_parser import RuleParser
            for ref in refs:
                ref_rule = ref["rule"]
                ref_subs = ref["subs"]

                ref_data = fetch_reference_rule(ref_rule)

                if ref_rule in printed_refs:
                    continue
                printed_refs.add(ref_rule)

                if ref_data:
                    ref_title, ref_text = ref_data

                    from app.services.rule_parser import RuleParser

                    filtered_text = RuleParser().filter_subsections(ref_text, ref_subs)

                    elements.append(Spacer(1, 10))
                    elements.append(
                        Paragraph(f"<b>Referenced Rule: {ref_rule}</b>", styles["Heading4"])
                    )
                    elements.append(Paragraph(ref_title, styles["Heading3"]))

                    # IMPORTANT
                    if isinstance(filtered_text, dict):
                        elements.extend(render(json.dumps(filtered_text)))
                    else:
                        elements.extend(render(filtered_text))
            elements.append(Spacer(1, 15))

    # GM
    if gm_list:
        elements.append(Paragraph("<b>GM</b>", styles["Heading2"]))

        for gm in gm_list:
            elements.append(Paragraph(gm["title"], styles["Heading3"]))
            elements.extend(render(gm["text"]))
            elements.append(Spacer(1, 15))

    doc.build(elements)

    return FileResponse(file_path, media_type="application/pdf")


# ================= SUBPART =================
@router.get("/subparts")
def get_subparts():
    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT subpart FROM rules")
    rows = cursor.fetchall()
    conn.close()

    return [r[0] for r in rows if r[0]]