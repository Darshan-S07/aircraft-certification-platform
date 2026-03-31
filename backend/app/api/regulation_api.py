import os
from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.regulation import Regulation
from app.models.rule import Rule
from app.services.rule_parser import RuleParser
import sqlite3
import json

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

    parser = RuleParser()
    text = parser.extract_text_from_pdf(file_path)
    text = parser.remove_toc(text)

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
        {"label": f"CS 23.{r[0]} - {r[1]}", "value": r[0]}
        for r in rows
    ]


# ================= FETCH REFERENCE =================
def fetch_reference_rule(ref):
    conn = sqlite3.connect("certification.db")
    cursor = conn.cursor()

    if ref.startswith("23."):
        ref_num = ref.replace("23.", "")
        cursor.execute("""
            SELECT title, text FROM rules
            WHERE rule_number = ? AND type = 'CS'
        """, (ref_num,))

    elif ref.startswith("VLA."):
        ref_num = ref.replace("VLA.", "")
        cursor.execute("""
            SELECT title, text FROM rules
            WHERE rule_number = ? AND type = 'CS'
        """, (ref_num,))
    else:
        return None

    row = cursor.fetchone()
    conn.close()
    return row


# ================= EXPORT PDF =================
@router.get("/export/{rule_number}")
def export_rule(rule_number: str):

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

        for amc in amc_list:
            elements.append(Paragraph(amc["title"], styles["Heading3"]))
            elements.extend(render(amc["text"]))

            refs = list(set(amc["references"]))
            from app.services.rule_parser import fetch_reference_rule
            for ref in refs:
                ref_rule = fetch_reference_rule(ref)

                if ref_rule:
                    elements.append(Spacer(1, 10))
                    elements.append(
                        Paragraph(f"<b>Referenced Rule: {ref}</b>", styles["Heading4"])
                    )
                    elements.append(Paragraph(ref_rule[0], styles["Heading3"]))
                    elements.extend(render(ref_rule[1]))

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