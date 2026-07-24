"""
PDF valuation report — a clean one/two-page tearsheet for any ticker.

Summarizes the fair value, scenarios, score and its drivers, key assumptions,
the cross-checks (reverse DCF, comps, Monte Carlo) and, when available, the AI
qualitative analysis. Built with reportlab (pure-Python, no system deps).
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)

NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#2E5FA3")
GREY = colors.HexColor("#666666")
LIGHT = colors.HexColor("#EEF2F9")
GREEN = colors.HexColor("#1B7F4B")
AMBER = colors.HexColor("#C77C11")
RED = colors.HexColor("#B3261E")


def _pct(x, nd=1):
    return f"{x*100:.{nd}f}%" if x is not None else "n/a"


def _money(x, nd=2):
    return f"${x:,.{nd}f}" if x is not None else "n/a"


def _score_color(s):
    return GREEN if s >= 66 else (AMBER if s >= 46 else RED)


def _hx(c):
    """reportlab Color -> '#rrggbb' for inline <font color=...> markup."""
    return "#" + c.hexval()[2:8]


def build_pdf(result, path: str) -> str:
    cd, sc, a, w = result.company, result.scenarios, result.assumptions, result.wacc
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=9, leading=12.5, textColor=colors.HexColor("#222222"))
    small = ParagraphStyle("small", parent=body, fontSize=7.5, textColor=GREY, leading=10)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                        fontSize=11, textColor=NAVY, spaceBefore=10, spaceAfter=4)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=10, bulletIndent=0, spaceAfter=1)

    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.6 * inch,
                            bottomMargin=0.6 * inch, leftMargin=0.65 * inch, rightMargin=0.65 * inch)
    E = []

    # ---- Header ----
    title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold",
                           fontSize=17, textColor=NAVY, spaceAfter=1, alignment=TA_LEFT)
    E.append(Paragraph(f"{cd.name} ({cd.ticker})", title))
    E.append(Paragraph(f"DCF Valuation &amp; Opportunity Score &nbsp;|&nbsp; {cd.sector or ''} "
                       f"{('· ' + cd.industry) if cd.industry else ''} &nbsp;|&nbsp; As of {cd.as_of}", small))
    E.append(Spacer(1, 6))
    E.append(HRFlowable(width="100%", thickness=1.4, color=NAVY, spaceAfter=8))

    # ---- Headline metrics band ----
    up = result.upside
    up_txt = _pct(up, 0) if up is not None else "n/a"
    up_col = GREEN if (up or 0) > 0 else RED
    headline = [
        [Paragraph("<b>Price</b>", small), Paragraph("<b>Base Fair Value</b>", small),
         Paragraph("<b>Upside</b>", small), Paragraph("<b>Score</b>", small),
         Paragraph("<b>Call</b>", small)],
        [Paragraph(f"<font size=13>{_money(cd.price)}</font>", body),
         Paragraph(f"<font size=13 color='#1F3864'><b>{_money(result.base_fair_value)}</b></font>", body),
         Paragraph(f"<font size=13 color='{_hx(up_col)}'><b>{up_txt}</b></font>", body),
         Paragraph(f"<font size=15 color='{_hx(_score_color(result.score.score))}'><b>{result.score.score}</b></font>"
                   f"<font size=8 color='#666666'>/100</font>", body),
         Paragraph(f"<font size=12 color='{_hx(_score_color(result.score.score))}'><b>{result.score.recommendation}</b></font>", body)],
    ]
    t = Table(headline, colWidths=[1.2 * inch] * 5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 4, colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    E.append(t)
    E.append(Spacer(1, 4))
    E.append(Paragraph(f"Regime: <b>{result.classification.regime}</b> &nbsp;·&nbsp; DCF reliability: "
                       f"<b>{result.classification.dcf_reliability}</b> &nbsp;·&nbsp; Score confidence: "
                       f"<b>{result.score.confidence}</b>", small))

    # ---- Two-column: scenarios + key metrics ----
    scen = [["Scenario", "Fair Value", "vs Price"],
            ["Bear", _money(sc.bear.per_share), _pct((sc.bear.per_share/cd.price-1) if cd.price else None, 0)],
            ["Base", _money(sc.base.per_share), _pct((sc.base.per_share/cd.price-1) if cd.price else None, 0)],
            ["Bull", _money(sc.bull.per_share), _pct((sc.bull.per_share/cd.price-1) if cd.price else None, 0)]]
    scen_t = Table(scen, colWidths=[0.9 * inch, 1.0 * inch, 0.8 * inch])
    scen_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    metrics = [
        ["WACC", _pct(w.wacc)], ["Rev growth (fwd)", _pct(result.classification.blended_growth)],
        ["Op margin → target", f"{_pct(a.current_margin,0)} → {_pct(a.target_margin,0)}"],
        ["Terminal growth", _pct(a.terminal_growth)], ["ROIC", _pct(cd.roic)],
        ["Net debt/EBITDA", (f"{cd.net_debt_to_ebitda:.1f}x" if cd.net_debt_to_ebitda is not None else "n/a")],
        ["Monte Carlo P(undervalued)", _pct(result.montecarlo.prob_undervalued, 0)],
        ["Comps fair value", _money(result.comps.comps_fair_value)],
    ]
    met_t = Table(metrics, colWidths=[1.7 * inch, 1.1 * inch])
    met_t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LINEBELOW", (0, -1), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
    ]))
    combo = Table([[scen_t, met_t]], colWidths=[2.9 * inch, 3.0 * inch])
    combo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    E.append(Paragraph("Scenarios &amp; Key Metrics", h2))
    E.append(combo)

    # ---- Score breakdown ----
    E.append(Paragraph("Score Breakdown", h2))
    subs = result.score.subscores
    wts = result.score.weights
    order = ["valuation", "quality", "growth", "health", "momentum"]
    sb = [["Factor", "Score", "Weight"]]
    for k in order:
        v = subs.get(k)
        sb.append([k.capitalize(), (f"{v:.0f}/100" if v is not None else "n/a"), _pct(wts.get(k, 0), 0)])
    sb_t = Table(sb, colWidths=[1.4 * inch, 1.0 * inch, 0.9 * inch])
    sb_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    E.append(sb_t)

    # ---- Reverse DCF ----
    E.append(Paragraph("What the Market Is Pricing In (Reverse DCF)", h2))
    E.append(Paragraph(result.reverse.growth_verdict or "n/a", body))
    if result.reverse.margin_verdict:
        E.append(Paragraph(result.reverse.margin_verdict, body))

    # ---- AI / analysis ----
    ai = result.ai
    if ai:
        E.append(Paragraph(f"Qualitative Analysis &nbsp;<font size=7 color='#888888'>({ai.get('source','')})</font>", h2))
        if ai.get("business_summary"):
            E.append(Paragraph(ai["business_summary"], body))
        if ai.get("moat"):
            E.append(Paragraph(f"<b>Moat ({ai['moat'].get('rating','')}):</b> {ai['moat'].get('text','')}", body))
        E.append(Spacer(1, 2))
        if ai.get("bull_thesis"):
            E.append(Paragraph(f"<b><font color='#1B7F4B'>Bull:</font></b> {ai['bull_thesis']}", body))
        if ai.get("bear_thesis"):
            E.append(Paragraph(f"<b><font color='#B3261E'>Bear:</font></b> {ai['bear_thesis']}", body))
        for label, key in [("Key risks", "key_risks"), ("Catalysts", "catalysts"),
                           ("Assumption critique", "assumption_critique")]:
            items = ai.get(key)
            if items:
                E.append(Paragraph(f"<b>{label}:</b>", body))
                for it in items:
                    E.append(Paragraph(f"• {it}", bullet))
        if ai.get("overall_take"):
            E.append(Spacer(1, 2))
            E.append(Paragraph(f"<b>Bottom line:</b> {ai['overall_take']}", body))

    # ---- Footer / disclaimer ----
    E.append(Spacer(1, 8))
    E.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC"), spaceAfter=4))
    E.append(Paragraph("Sources: " + "; ".join(cd.sources[:6]), small))
    E.append(Paragraph("Educational tool, not investment advice. Automated DCF assumptions are estimates; "
                       "verify against primary filings before acting. Generated by the Adaptive DCF Valuation Tool.", small))

    doc.build(E)
    return path
