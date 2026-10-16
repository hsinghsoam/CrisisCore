import io
import csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_sitrep_pdf(incidents_list: list, stats: dict, official_name: str = "Disaster Operations Officer") -> io.BytesIO:
    """
    Generates an official National/State Disaster Management Situation Report (SITREP) PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )
    section_heading = ParagraphStyle(
        'SectionHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("CRISISCORE // EMERGENCY SITUATION REPORT (SITREP)", title_style))
    elements.append(Paragraph(
        f"<b>Prepared By:</b> {official_name} | <b>Generated:</b> {datetime.now().strftime('%d %b %Y, %H:%M:%S IST')} | <b>Security Clearance:</b> OFFICIAL / OPERATIONAL SENSITIVE",
        subtitle_style
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#CBD5E1'), spaceAfter=12))
    
    # Key Operational Metrics Table
    elements.append(Paragraph("1. EXECUTIVE DISASTER SUMMARY & METRICS", section_heading))
    metrics_data = [
        [
            Paragraph("<b>Total Active Reports</b>", cell_bold),
            Paragraph("<b>Critical Urgency</b>", cell_bold),
            Paragraph("<b>Total Affected</b>", cell_bold),
            Paragraph("<b>Total Injured</b>", cell_bold),
            Paragraph("<b>Deployed Teams</b>", cell_bold)
        ],
        [
            Paragraph(str(stats.get('total_incidents', len(incidents_list))), cell_style),
            Paragraph(str(stats.get('critical_count', 0)), cell_style),
            Paragraph(str(stats.get('total_affected', 0)), cell_style),
            Paragraph(str(stats.get('total_injured', 0)), cell_style),
            Paragraph(str(stats.get('active_rescue_teams', 0)), cell_style)
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[100, 100, 100, 100, 120])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 14))
    
    # Incident Registry Table
    elements.append(Paragraph("2. VERIFIED INCIDENT LOG & RESCUE DISPATCH STATUS", section_heading))
    inc_headers = [
        Paragraph("<b>Tracking ID</b>", cell_bold),
        Paragraph("<b>Disaster & Location</b>", cell_bold),
        Paragraph("<b>Priority</b>", cell_bold),
        Paragraph("<b>Affected / Injured</b>", cell_bold),
        Paragraph("<b>Status</b>", cell_bold),
        Paragraph("<b>Gov Sync</b>", cell_bold)
    ]
    table_rows = [inc_headers]
    
    for inc in incidents_list[:30]:  # Up to top 30 in PDF
        p_lvl = inc.get('priority_level', 'MED')
        p_score = inc.get('priority_score', 0)
        
        row = [
            Paragraph(inc.get('tracking_id', ''), cell_bold),
            Paragraph(f"<b>{inc.get('disaster_type', '')}</b><br/>{inc.get('district', '')}, {inc.get('state', '')}", cell_style),
            Paragraph(f"<b>{p_lvl}</b> ({p_score}/100)", cell_style),
            Paragraph(f"Aff: {inc.get('affected_count', 0)}<br/>Inj: {inc.get('injured_count', 0)}", cell_style),
            Paragraph(f"{inc.get('status', 'Submitted')}", cell_style),
            Paragraph(f"{inc.get('government_sync_status', 'NOT_FORWARDED')}", cell_style)
        ]
        table_rows.append(row)
        
    inc_table = Table(table_rows, colWidths=[95, 140, 75, 70, 75, 75])
    inc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(inc_table)
    elements.append(Spacer(1, 14))
    
    # Official Footer & Disclaimer
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceAfter=8))
    disclaimer_text = (
        "<b>LEGAL & COMPLIANCE NOTICE:</b> This report is generated by CrisisCore Emergency Platform. "
        "Verified emergency transmissions adhere to OASIS CAP v1.2 specifications and NDMA standard operating protocols. "
        "Dispatches marked PENDING_MANUAL_REVIEW require authorization before field action."
    )
    elements.append(Paragraph(disclaimer_text, ParagraphStyle('Disc', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=9, textColor=colors.HexColor('#64748B'))))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_incidents_csv(incidents_list: list) -> str:
    """
    Generates a CSV string of incidents.
    """
    output = io.StringIO()
    fieldnames = [
        "tracking_id", "disaster_type", "priority_level", "priority_score",
        "status", "state", "district", "address", "lat", "lng",
        "affected_count", "injured_count", "children_count", "elderly_count",
        "assistance_required", "citizen_name", "phone", "government_sync_status",
        "created_at"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for inc in incidents_list:
        writer.writerow(inc)
    return output.getvalue()
