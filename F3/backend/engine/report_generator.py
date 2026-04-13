from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import io
from datetime import datetime

BLUE   = colors.HexColor("#1A237E"); LBLUE = colors.HexColor("#1565C0")
CYAN   = colors.HexColor("#00BCD4"); BG    = colors.HexColor("#E8EAF6")
RED    = colors.HexColor("#B71C1C"); GREEN = colors.HexColor("#1B5E20")
GREY   = colors.HexColor("#546E7A"); WHITE = colors.white
WARN   = colors.HexColor("#E65100")

def _ts(s): return TableStyle(s)
def _hdr(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(BLUE); canvas.rect(0, h-18*mm, w, 18*mm, fill=1, stroke=0)
    canvas.setFillColor(CYAN); canvas.rect(0, h-20*mm, w, 2*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 10); canvas.setFillColor(WHITE)
    canvas.drawString(18*mm, h-13*mm, "ENGINEERING CHANGE IMPACT SUMMARY REPORT")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w-18*mm, h-13*mm, f"ECA v2.0 | {datetime.now().strftime('%Y-%m-%d')} | Page {doc.page}")
    canvas.setFillColor(colors.HexColor("#F8FAFF"))
    canvas.rect(0, 0, w, 11*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7); canvas.setFillColor(GREY)
    canvas.drawCentredString(w/2, 4*mm, "CONFIDENTIAL — ENGINEERING CHANGE DOCUMENT | STARK-X | SLB PROTOTYPE")
    canvas.restoreState()

BASE_TS = [
    ("BACKGROUND",(0,0),(-1,0), BLUE), ("TEXTCOLOR",(0,0),(-1,0), WHITE),
    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 9),
    ("FONTSIZE",(0,1),(-1,-1), 8.5),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, BG]),
    ("GRID",(0,0),(-1,-1), 0.4, colors.HexColor("#90A4AE")),
    ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ("LEFTPADDING",(0,0),(-1,-1), 7),
]

def generate_pdf(parsed, impact, revision, effort, narrative="") -> bytes:
    buf = io.BytesIO()
    W = 174*mm
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=28*mm, bottomMargin=18*mm)
    E = []
    s_title = ParagraphStyle("t", fontSize=18, fontName="Helvetica-Bold",
                              textColor=WHITE, alignment=TA_CENTER)
    s_sec = ParagraphStyle("s", fontSize=12, fontName="Helvetica-Bold",
                            textColor=BLUE, spaceBefore=14, spaceAfter=6)
    s_body = ParagraphStyle("b", fontSize=9, fontName="Helvetica",
                             textColor=colors.HexColor("#212121"), leading=14, spaceAfter=4)
    s_narr = ParagraphStyle("n", fontSize=9.5, fontName="Helvetica", leading=15,
                             alignment=TA_JUSTIFY, textColor=BLUE, spaceAfter=6)
    s_cap = ParagraphStyle("c", fontSize=8, fontName="Helvetica",
                            textColor=GREY, alignment=TA_CENTER)

    def hr(): return HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=6)
    def sec(n, t): return Paragraph(f"{n}. {t}", s_sec)
    def sp(n=4): return Spacer(1, n*mm)

    # Cover
    E += [sp(30)]
    cover = Table([[Paragraph("CHANGE IMPACT SUMMARY REPORT", s_title)],
                   [Paragraph("Engineering Change Assistant — ECA System v2.0 | Team STARK-X", ParagraphStyle("cs",fontSize=10,fontName="Helvetica",textColor=colors.HexColor("#90CAF9"),alignment=TA_CENTER))]], colWidths=[W])
    cover.setStyle(_ts([("BACKGROUND",(0,0),(-1,-1),BLUE),("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12)]))
    E.append(cover); E.append(sp(6))

    rev = revision["revision_type"]
    rc = RED if rev == "Major" else GREEN
    rbg = colors.HexColor("#FFEBEE") if rev == "Major" else colors.HexColor("#E8F5E9")
    rl = f"{'MAJOR' if rev=='Major' else 'MINOR'} REVISION — {revision['revision_label']}"
    rb = Table([[Paragraph(rl, ParagraphStyle("rb",fontSize=14,fontName="Helvetica-Bold",textColor=rc,alignment=TA_CENTER))]], colWidths=[W])
    rb.setStyle(_ts([("BACKGROUND",(0,0),(-1,-1),rbg),("BOX",(0,0),(-1,-1),2,rc),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    E.append(rb); E.append(sp(6))

    s = impact["summary"]
    meta = Table([
        ["Document No:", f"ECA-{datetime.now().strftime('%Y%m%d-%H%M')}", "Issued By:", "ECA System v2.0"],
        ["Date:", datetime.now().strftime("%Y-%m-%d %H:%M"), "Status:", "DRAFT — Pending Approval"],
    ], colWidths=[38*mm, 55*mm, 35*mm, 46*mm])
    meta.setStyle(_ts([("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
                       ("FONTSIZE",(0,0),(-1,-1),8.5),("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#BDBDBD")),
                       ("BACKGROUND",(0,0),(-1,-1),BG),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),6)]))
    E.append(meta); E.append(sp(6))

    dash = Table([["METRIC","VALUE","STATUS"],
                  ["Parts Affected", str(s["total_parts_affected"]), "Review Required"],
                  ["Assemblies Impacted", str(s["total_assemblies_affected"]), "Traced"],
                  ["Inspection Steps to Update", str(s["total_inspection_steps_to_update"]), "Update Required"],
                  ["Documents to Revise", str(s["total_documents_to_update"]), f"{s['high_priority_documents']} HIGH PRIORITY"],
                  ["Safety-Critical Assemblies", str(s["safety_critical_assemblies"]), "Mandatory Re-cert" if s["safety_critical_assemblies"] else "None"],
                  ["Estimated Effort", f"{effort['total_hours']}h ({effort['total_days']} days)", f"~${effort['cost_estimate_usd']:,} USD"]],
                 colWidths=[80*mm, 52*mm, 42*mm])
    dash.setStyle(_ts(BASE_TS))
    E.append(Paragraph("IMPACT DASHBOARD", s_sec)); E.append(hr()); E.append(dash)
    E.append(PageBreak())

    # S1
    E.append(sec("1","CHANGE REQUEST")); E.append(hr())
    cr = Table([["Field","Value"],
                ["Interpreted Request", parsed.get("understood_request","")],
                ["Change Category", parsed.get("change_category","").title()],
                ["Pressure Boundary", "YES" if parsed.get("affects_pressure_boundary") else "No"],
                ["Material Change", f"YES -> {parsed.get('new_material','')}" if parsed.get("material_change") else "No"],
                ["AI Confidence", parsed.get("confidence","").title()]], colWidths=[55*mm, 119*mm])
    cr.setStyle(_ts(BASE_TS)); E.append(cr); E.append(sp(4))

    if parsed.get("changes"):
        ch = Table([["Part","Parameter","Current","New","Delta","Delta%","Unit"]] +
                   [[c["part_id"],c.get("parameter","").replace("_mm","").replace("_"," ").title(),
                     str(c.get("current_value","—")),str(c.get("new_value","—")),
                     f"{c.get('delta',0):+.2f}",f"{c.get('delta_pct',0):+.1f}%",c.get("unit","mm")]
                    for c in parsed["changes"]],
                   colWidths=[22*mm,38*mm,22*mm,22*mm,22*mm,22*mm,16*mm])
        ch.setStyle(_ts(BASE_TS)); E.append(ch); E.append(sp(4))

    # S2
    E.append(sec("2","REVISION CLASSIFICATION")); E.append(hr())
    rc2 = Table([["Revision Type","Label","ECO Required","Engineering Hold"],
                 [rev, revision["revision_label"],
                  "YES" if rev=="Major" else "NO",
                  "YES — STOP" if revision.get("requires_engineering_hold") else "No"]],
                colWidths=[44*mm,46*mm,40*mm,44*mm])
    rc2.setStyle(_ts(BASE_TS + [("TEXTCOLOR",(0,1),(0,1),RED if rev=="Major" else GREEN),("FONTNAME",(0,1),(-1,1),"Helvetica-Bold")])); E.append(rc2)
    E.append(sp(3)); E.append(Paragraph(revision.get("revision_note",""), s_body))

    # S3
    E.append(sec("3","AFFECTED PARTS")); E.append(hr())
    pt = Table([["Part ID","Name","Material","Rev","Impact","Action"]] +
               [[p["part_id"],p["part_name"],p["material"],p["current_revision"],
                 p["impact_type"].replace("_"," ").title(),p["action_required"]]
                for p in impact["affected_parts"]],
               colWidths=[20*mm,35*mm,20*mm,16*mm,35*mm,48*mm])
    pt.setStyle(_ts(BASE_TS)); E.append(pt)

    # S4
    E.append(sec("4","ASSEMBLY IMPACT")); E.append(hr())
    at = Table([["Assembly ID","Assembly Name","Criticality","Impact","BOM","Test Proc"]] +
               [[a["assembly_id"],a["assembly_name"],a["criticality"].replace("_"," ").title(),
                 a["impact_type"].replace("_"," ").title(),a.get("bom_id","—"),a.get("test_procedure_id","—")]
                for a in impact["affected_assemblies"]],
               colWidths=[22*mm,55*mm,26*mm,26*mm,24*mm,21*mm])
    ast = _ts(BASE_TS)
    for i,a in enumerate(impact["affected_assemblies"],1):
        if a["criticality"]=="safety_critical": ast.add("BACKGROUND",(0,i),(-1,i),colors.HexColor("#FFF3E0"))
    at.setStyle(ast); E.append(at)

    # S5
    E.append(sec("5","INSPECTION PLAN IMPACT")); E.append(hr())
    if impact["affected_inspection_steps"]:
        it = Table([["Part","Plan","Step","Type","Description","Action"]] +
                   [[s["part_name"],s["inspection_plan_id"],str(s["step_number"]),s.get("step_type","").title(),
                     s["step_description"][:50]+"..." if len(s["step_description"])>50 else s["step_description"],"UPDATE"]
                    for s in impact["affected_inspection_steps"]],
                   colWidths=[28*mm,20*mm,12*mm,16*mm,68*mm,18*mm])
        it.setStyle(_ts(BASE_TS + [("TEXTCOLOR",(-1,1),(-1,-1),WARN),("FONTNAME",(-1,1),(-1,-1),"Helvetica-Bold")])); E.append(it)
    else:
        E.append(Paragraph("No inspection steps directly impacted.", s_body))

    # S6
    E.append(sec("6","DOCUMENT IMPACT REGISTER")); E.append(hr())
    dt = Table([["Document Type","Reference","Action","Priority"]] +
               [[d["document_type"],d["reference"],d["action"],d["priority"].upper()]
                for d in impact["document_impacts"]],
               colWidths=[42*mm,62*mm,50*mm,20*mm])
    dts = _ts(BASE_TS)
    for i,d in enumerate(impact["document_impacts"],1):
        if d["priority"]=="high": dts.add("TEXTCOLOR",(3,i),(3,i),RED); dts.add("FONTNAME",(3,i),(3,i),"Helvetica-Bold")
    dt.setStyle(dts); E.append(dt)

    # S7 Safety
    if impact["safety_warnings"]:
        E.append(sec("7","SAFETY WARNINGS")); E.append(HRFlowable(width="100%",thickness=2,color=RED,spaceAfter=6))
        wt = Table([["Severity","Part","Message","Action"]] +
                   [[w["severity"],w.get("part_id","—"),w["message"],w["action"]]
                    for w in impact["safety_warnings"]],
                   colWidths=[22*mm,20*mm,70*mm,62*mm])
        wst = _ts([("BACKGROUND",(0,0),(-1,0),RED),("TEXTCOLOR",(0,0),(-1,0),WHITE),
                   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),
                   ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#FFEBEE"),WHITE]),
                   ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#BDBDBD")),
                   ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),7)])
        wt.setStyle(wst); E.append(wt)
        sn = "8"
    else:
        sn = "7"

    # Effort
    E.append(sec(sn,"ENGINEERING EFFORT ESTIMATE")); E.append(hr())
    ef = Table([["Total Hours",f"{effort['total_hours']}h"],["Total Days",f"{effort['total_days']} days"],
                ["Estimated Cost (USD)",f"${effort['cost_estimate_usd']:,}"],
                ["Basis",effort.get("basis","")],["Confidence",effort.get("confidence","")]],
               colWidths=[70*mm,104*mm])
    ef.setStyle(_ts(BASE_TS)); E.append(ef); E.append(sp(3))
    bd = Table([["Activity","Hours","%"]] +
               [[k,str(v),f"{v/max(effort['total_hours'],1)*100:.0f}%"] for k,v in effort["breakdown"].items()],
               colWidths=[100*mm,37*mm,37*mm])
    bd.setStyle(_ts(BASE_TS)); E.append(bd)

    if narrative:
        E.append(sec(str(int(sn)+1),"ENGINEERING IMPACT NARRATIVE")); E.append(hr())
        E.append(Paragraph(narrative, s_narr))

    # Sign-off
    E.append(sp(8))
    so = Table([["PREPARED BY","REVIEWED BY","APPROVED BY"],
                ["ECA System v2.0\nAI Engineering Assistant","_______________________\nEngineering Lead","_______________________\nPrincipal Engineer"],
                [datetime.now().strftime("%Y-%m-%d %H:%M"),"Date: _______________","Date: _______________"]],
               colWidths=[58*mm,58*mm,58*mm])
    so.setStyle(_ts([("BACKGROUND",(0,0),(-1,0),BLUE),("TEXTCOLOR",(0,0),(-1,0),WHITE),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                     ("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#BDBDBD")),
                     ("ALIGN",(0,0),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    E.append(so)

    doc.build(E, onFirstPage=_hdr, onLaterPages=_hdr)
    buf.seek(0); return buf.getvalue()
