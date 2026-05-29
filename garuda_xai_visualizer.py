"""
garuda_xai_visualizer.py
========================
Pure visualisation layer.  Builds:
    1. render_sector_treemap()        - Plotly treemap of allocated capital
    2. render_xai_gauge()              - Horizontal stacked bar of XAI weights
    3. render_projection_heatmap()     - Scatter of Net Profit vs Holding Days
    4. generate_tear_sheet_image()     - PIL PNG infographic per recommendation

Every helper accepts the dataclasses / dicts produced by
garuda_quant_engine.py and returns either a Plotly Figure or raw PNG bytes.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont

from garuda_config_assets import THEME


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _positions_to_df(positions: Iterable) -> pd.DataFrame:
    rows = []
    for p in positions:
        rows.append({
            "Ticker": p.ticker,
            "Sector": p.sector,
            "Quantity": p.quantity,
            "Entry": p.entry_price,
            "Capital Used (₹)": p.capital_used,
            "Target": p.target_price,
            "Stop": p.stop_loss,
            "Holding (Days)": p.expected_holding_days,
            "Gross (₹)": p.gross_profit,
            "Fees (₹)": p.total_fees,
            "Net Profit (₹)": p.net_profit,
            "Composite": p.composite_score,
        })
    return pd.DataFrame(rows)


def _apply_dark_layout(fig: go.Figure, height: int = 480) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=THEME["BG_DEEP"],
        plot_bgcolor=THEME["BG_PANEL"],
        font=dict(color=THEME["TEXT_PRIMARY"], family="Inter, Arial, sans-serif"),
        margin=dict(l=20, r=20, t=60, b=20),
        height=height,
        legend=dict(bgcolor=THEME["BG_PANEL"], bordercolor=THEME["BORDER"]),
    )
    return fig


# ---------------------------------------------------------------------------
# 1.  Sector Treemap
# ---------------------------------------------------------------------------
def render_sector_treemap(positions: Iterable) -> go.Figure:
    df = _positions_to_df(positions)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No allocations to display",
            showarrow=False,
            font=dict(color=THEME["TEXT_MUTED"], size=16),
        )
        return _apply_dark_layout(fig, 420)

    df["Label"] = df.apply(
        lambda r: f"{r['Ticker']}<br>₹{r['Capital Used (₹)']:,.0f}<br>Qty {int(r['Quantity'])}",
        axis=1,
    )
    fig = px.treemap(
        df,
        path=[px.Constant("Garuda Portfolio"), "Sector", "Label"],
        values="Capital Used (₹)",
        color="Net Profit (₹)",
        color_continuous_scale=[
            (0.0, THEME["ACCENT_CRIMSON"]),
            (0.5, THEME["BG_CARD"]),
            (1.0, THEME["ACCENT_MINT"]),
        ],
    )
    fig.update_traces(
        textfont=dict(color=THEME["TEXT_PRIMARY"], size=13),
        marker=dict(line=dict(color=THEME["BG_DEEP"], width=2)),
        hovertemplate="<b>%{label}</b><br>Capital: ₹%{value:,.0f}<extra></extra>",
    )
    fig.update_layout(title="Sector Capital Treemap")
    return _apply_dark_layout(fig, 520)


# ---------------------------------------------------------------------------
# 2.  XAI Horizontal Stacked Bar
# ---------------------------------------------------------------------------
def render_xai_gauge(contributions: dict[str, float], ticker: str = "") -> go.Figure:
    if not contributions:
        fig = go.Figure()
        fig.add_annotation(text="No XAI data", showarrow=False, font=dict(color=THEME["TEXT_MUTED"]))
        return _apply_dark_layout(fig, 320)

    labels = list(contributions.keys())
    values = list(contributions.values())
    palette = [
        THEME["ACCENT_INDIGO"],
        THEME["ACCENT_MINT"],
        THEME["ACCENT_AMBER"],
        THEME["ACCENT_CRIMSON"],
    ]
    fig = go.Figure()
    for i, (lbl, val) in enumerate(zip(labels, values)):
        fig.add_trace(go.Bar(
            x=[val],
            y=["Signal Mix"],
            orientation="h",
            name=lbl,
            text=[f"{lbl}: {val:.1f}%"],
            textposition="inside",
            insidetextanchor="middle",
            marker=dict(color=palette[i % len(palette)], line=dict(color=THEME["BG_DEEP"], width=1)),
            hovertemplate=f"{lbl}: %{{x:.1f}}%<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title=f"XAI Feature Attribution{(' — ' + ticker) if ticker else ''}",
        xaxis=dict(range=[0, 100], showgrid=False, ticksuffix="%",
                   color=THEME["TEXT_MUTED"]),
        yaxis=dict(showgrid=False, color=THEME["TEXT_MUTED"]),
        showlegend=False,
    )
    return _apply_dark_layout(fig, 280)


# ---------------------------------------------------------------------------
# 3.  Projection Heatmap (Net Profit vs Holding Days)
# ---------------------------------------------------------------------------
def render_projection_heatmap(positions: Iterable) -> go.Figure:
    df = _positions_to_df(positions)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No projections to display", showarrow=False,
                           font=dict(color=THEME["TEXT_MUTED"]))
        return _apply_dark_layout(fig, 420)

    fig = px.scatter(
        df,
        x="Holding (Days)",
        y="Net Profit (₹)",
        size="Capital Used (₹)",
        color="Composite",
        text="Ticker",
        color_continuous_scale=[
            (0.0, THEME["ACCENT_INDIGO"]),
            (0.5, THEME["ACCENT_AMBER"]),
            (1.0, THEME["ACCENT_MINT"]),
        ],
        size_max=48,
    )
    fig.update_traces(
        textposition="top center",
        textfont=dict(color=THEME["TEXT_PRIMARY"], size=11),
        marker=dict(line=dict(color=THEME["BG_DEEP"], width=1.5)),
    )
    fig.update_layout(
        title="Projected Net Profit vs Expected Holding Time",
        xaxis=dict(gridcolor=THEME["BORDER"], color=THEME["TEXT_MUTED"]),
        yaxis=dict(gridcolor=THEME["BORDER"], color=THEME["TEXT_MUTED"]),
    )
    return _apply_dark_layout(fig, 500)


# ---------------------------------------------------------------------------
# 4.  Tear-Sheet PNG generator (Pillow)
# ---------------------------------------------------------------------------
def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def generate_tear_sheet_image(position, contributions: dict[str, float] | None = None) -> bytes:
    """Build a 1080x1350 PNG infographic for one allocated position."""
    W, H = 1080, 1350
    bg = _hex_to_rgb(THEME["BG_DEEP"])
    panel = _hex_to_rgb(THEME["BG_PANEL"])
    card = _hex_to_rgb(THEME["BG_CARD"])
    text_p = _hex_to_rgb(THEME["TEXT_PRIMARY"])
    text_m = _hex_to_rgb(THEME["TEXT_MUTED"])
    mint = _hex_to_rgb(THEME["ACCENT_MINT"])
    crimson = _hex_to_rgb(THEME["ACCENT_CRIMSON"])
    indigo = _hex_to_rgb(THEME["ACCENT_INDIGO"])
    amber = _hex_to_rgb(THEME["ACCENT_AMBER"])

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # --- Header band ---------------------------------------------------
    draw.rectangle([0, 0, W, 130], fill=panel)
    draw.text((40, 30), "GARUDA-OPS  ::  TEAR-SHEET", font=_load_font(34, True), fill=mint)
    draw.text((40, 80), f"Generated {datetime.now().strftime('%d %b %Y · %H:%M IST')}",
              font=_load_font(20), fill=text_m)

    # --- Ticker card ---------------------------------------------------
    draw.rectangle([40, 160, W - 40, 320], fill=card, outline=indigo, width=2)
    draw.text((60, 180), position.ticker, font=_load_font(56, True), fill=text_p)
    draw.text((60, 250), f"Sector: {position.sector}", font=_load_font(22), fill=text_m)
    draw.text((60, 282), f"Composite Score: {position.composite_score:.2f}",
              font=_load_font(20), fill=amber)

    # --- Trade parameters ---------------------------------------------
    draw.rectangle([40, 350, W - 40, 690], fill=card, outline=indigo, width=2)
    draw.text((60, 365), "TRADE BLUEPRINT", font=_load_font(24, True), fill=mint)

    rows = [
        ("Entry Price",       f"₹{position.entry_price:,.2f}", text_p),
        ("Target",            f"₹{position.target_price:,.2f}", mint),
        ("Stop Loss",         f"₹{position.stop_loss:,.2f}", crimson),
        ("Quantity",          f"{position.quantity:,} shares", text_p),
        ("Capital Deployed",  f"₹{position.capital_used:,.2f}", text_p),
        ("Holding Window",    f"{position.expected_holding_days} trading days", amber),
        ("Gross Profit",      f"₹{position.gross_profit:,.2f}", text_p),
        ("Total Fees",        f"₹{position.total_fees:,.2f}", text_m),
        ("Net Profit",        f"₹{position.net_profit:,.2f}",
            mint if position.net_profit >= 0 else crimson),
    ]
    y = 410
    label_font = _load_font(20)
    value_font = _load_font(22, True)
    for label, val, colour in rows:
        draw.text((80, y), label, font=label_font, fill=text_m)
        draw.text((520, y), val, font=value_font, fill=colour)
        y += 30

    # --- XAI strip ----------------------------------------------------
    contribs = contributions or position.contributions or {}
    draw.rectangle([40, 720, W - 40, 1030], fill=card, outline=indigo, width=2)
    draw.text((60, 735), "EXPLAINABLE-AI ATTRIBUTION", font=_load_font(24, True), fill=mint)

    # Stacked horizontal bar
    bar_x0, bar_y0, bar_x1, bar_y1 = 60, 790, W - 60, 840
    draw.rectangle([bar_x0, bar_y0, bar_x1, bar_y1], fill=panel)
    palette = [indigo, mint, amber, crimson]
    cursor = bar_x0
    total = sum(contribs.values()) or 1.0
    items = list(contribs.items())
    for i, (lbl, val) in enumerate(items):
        width = int((val / total) * (bar_x1 - bar_x0))
        draw.rectangle([cursor, bar_y0, cursor + width, bar_y1], fill=palette[i % len(palette)])
        cursor += width

    # Legend below bar
    leg_y = 870
    for i, (lbl, val) in enumerate(items):
        swatch_x = 70 + (i % 2) * 480
        swatch_y = leg_y + (i // 2) * 35
        draw.rectangle([swatch_x, swatch_y, swatch_x + 22, swatch_y + 22],
                       fill=palette[i % len(palette)])
        draw.text((swatch_x + 32, swatch_y - 2),
                  f"{lbl}: {val:.1f}%", font=_load_font(18), fill=text_p)

    # --- Footer warning -----------------------------------------------
    draw.rectangle([40, 1060, W - 40, 1280], fill=panel, outline=crimson, width=2)
    draw.text((60, 1075), "COMPLIANCE & RISK WARNING", font=_load_font(22, True), fill=crimson)
    warning = (
        "This output is generated by an algorithmic engine for educational and\n"
        "research purposes only and does NOT constitute investment advice under\n"
        "SEBI (Investment Advisers) Regulations, 2013. All projections assume\n"
        "ideal liquidity and ignore slippage. Past performance and back-tested\n"
        "ghost-results do not guarantee future returns. Consult a SEBI-registered\n"
        "adviser before deploying capital."
    )
    draw.multiline_text((60, 1110), warning, font=_load_font(17), fill=text_m, spacing=4)

    # Footer brand bar
    draw.rectangle([0, H - 50, W, H], fill=panel)
    draw.text((40, H - 38), "Garuda-Ops · Cybernetic Indigo Edition",
              font=_load_font(18, True), fill=mint)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
