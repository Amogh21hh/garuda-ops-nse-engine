"""
app_garuda_main.py
==================
Garuda-Ops — Cybernetic Indigo institutional terminal for retail traders.

This revision adds two "unlock" sliders in the sidebar:
    * Max Risk Per Trade (%)   1..100   (100 unlocks aggressive knapsack)
    * Live Scan Limit          10..100  (random sample from ~375 universe)

Launch:
    streamlit run app_garuda_main.py
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

try:
    from streamlit_lottie import st_lottie
    LOTTIE_OK = True
except Exception:                       # pragma: no cover
    LOTTIE_OK = False

from garuda_config_assets import (
    LOTTIE_ASSETS,
    NSE_UNIVERSE,
    RISK_PROFILES,
    THEME,
)
from garuda_quant_engine import (
    GhostTester,
    run_full_pipeline,
)
from garuda_xai_visualizer import (
    generate_tear_sheet_image,
    render_projection_heatmap,
    render_sector_treemap,
    render_xai_gauge,
)


# =========================================================================
# Page config & global CSS
# =========================================================================
st.set_page_config(
    page_title="Garuda-Ops · Institutional Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = f"""
<style>
    .stApp {{
        background: radial-gradient(ellipse at top, #131A2C 0%, {THEME['BG_DEEP']} 60%, #05070D 100%);
        color: {THEME['TEXT_PRIMARY']};
    }}
    section[data-testid="stSidebar"] > div {{
        background: linear-gradient(180deg, {THEME['BG_PANEL']} 0%, #0A0F1B 100%);
        border-right: 1px solid {THEME['BORDER']};
    }}
    h1, h2, h3, h4 {{ color: {THEME['TEXT_PRIMARY']}; letter-spacing: 0.5px; }}
    .garuda-banner {{
        background: linear-gradient(120deg, {THEME['BG_PANEL']} 0%, #0E1626 100%);
        border: 1px solid {THEME['BORDER']};
        border-left: 4px solid {THEME['ACCENT_MINT']};
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 18px;
    }}
    .garuda-banner h1 {{
        margin: 0;
        font-size: 30px;
        background: linear-gradient(90deg, {THEME['ACCENT_MINT']}, {THEME['ACCENT_INDIGO']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .garuda-banner p {{ margin: 6px 0 0; color: {THEME['TEXT_MUTED']}; font-size: 14px; }}

    .kpi-card {{
        background: {THEME['BG_CARD']};
        border: 1px solid {THEME['BORDER']};
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 0 18px rgba(99, 102, 241, 0.05);
    }}
    .kpi-label {{
        color: {THEME['TEXT_MUTED']};
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }}
    .kpi-value {{ color: {THEME['TEXT_PRIMARY']}; font-size: 26px; font-weight: 700; margin-top: 4px; }}
    .kpi-value.mint   {{ color: {THEME['ACCENT_MINT']}; }}
    .kpi-value.amber  {{ color: {THEME['ACCENT_AMBER']}; }}
    .kpi-value.crimson{{ color: {THEME['ACCENT_CRIMSON']}; }}

    @keyframes garuda-pulse {{
        0%   {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.55); }}
        70%  {{ box-shadow: 0 0 0 14px rgba(16, 185, 129, 0);  }}
        100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);     }}
    }}
    @keyframes garuda-pulse-red {{
        0%   {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.55); }}
        70%  {{ box-shadow: 0 0 0 14px rgba(239, 68, 68, 0);  }}
        100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);     }}
    }}
    .buy-pulse {{
        display: inline-block;
        background: {THEME['ACCENT_MINT']};
        color: #042F1E;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        letter-spacing: 1.5px;
        animation: garuda-pulse 1.6s infinite;
    }}
    .unlocked-pulse {{
        display: inline-block;
        background: {THEME['ACCENT_CRIMSON']};
        color: #2A0606;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        letter-spacing: 1.5px;
        animation: garuda-pulse-red 1.4s infinite;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px; background: {THEME['BG_PANEL']}; padding: 6px;
        border-radius: 12px; border: 1px solid {THEME['BORDER']};
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; color: {THEME['TEXT_MUTED']};
        border-radius: 8px; padding: 10px 18px; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background: {THEME['BG_CARD']} !important;
        color: {THEME['ACCENT_MINT']} !important;
        border: 1px solid {THEME['ACCENT_INDIGO']};
    }}
    .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(120deg, {THEME['ACCENT_INDIGO']}, {THEME['ACCENT_MINT']});
        color: #04121A; border: 0; font-weight: 700;
        padding: 10px 22px; border-radius: 10px; letter-spacing: 0.6px;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        filter: brightness(1.1); transform: translateY(-1px);
    }}
    [data-testid="stDataFrame"] {{
        border: 1px solid {THEME['BORDER']};
        border-radius: 12px; overflow: hidden;
    }}
    .compliance-box {{
        background: {THEME['BG_PANEL']};
        border: 1px solid {THEME['ACCENT_CRIMSON']};
        border-left: 4px solid {THEME['ACCENT_CRIMSON']};
        padding: 14px 18px; border-radius: 10px;
        color: {THEME['TEXT_PRIMARY']}; font-size: 13px; line-height: 1.55;
    }}
    .unlock-note {{
        background: rgba(239, 68, 68, 0.08);
        border: 1px dashed {THEME['ACCENT_CRIMSON']};
        color: {THEME['TEXT_PRIMARY']};
        padding: 10px 14px; border-radius: 10px;
        font-size: 12.5px; margin-top: 8px;
    }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================================================================
# Lottie helpers
# =========================================================================
@st.cache_data(show_spinner=False, ttl=3600)
def _load_lottie(url: str):
    try:
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def show_lottie(key: str, height: int = 160):
    if not LOTTIE_OK:
        return
    data = _load_lottie(LOTTIE_ASSETS.get(key, ""))
    if data:
        st_lottie(data, height=height, loop=True, key=f"lottie_{key}_{id(data)}")


# =========================================================================
# Banner
# =========================================================================
st.markdown(
    """
    <div class="garuda-banner">
        <h1>🦅 Garuda-Ops · Cybernetic Indigo Terminal</h1>
        <p>Nifty-broad random scan · Aggressive knapsack mode ·
        Explainable AI · 100% capital utilisation</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================================
# Sidebar — Mission parameters + UNLOCK sliders
# =========================================================================
with st.sidebar:
    st.markdown("### ⚙️ Mission Parameters")

    capital = st.number_input(
        "Deployable Capital (₹)",
        min_value=1_000,
        max_value=10_00_000,
        value=5_000,
        step=1_000,
        help="Total INR to be allocated by the Greedy Knapsack engine.",
    )

    risk_label = st.selectbox(
        "Risk Tolerance Profile",
        list(RISK_PROFILES.keys()),
        index=1,
        help="Governs Hurst threshold, ATR target distance, and sector cap.",
    )

    st.markdown("---")
    st.markdown("#### 🔓 Unlock Limits")

    risk_per_trade_pct = st.slider(
        "Max Risk Per Trade (%)",
        min_value=1,
        max_value=100,
        value=25,
        step=1,
        help=(
            "How much of total capital ONE position may absorb. "
            "Set to 100 to UNLOCK aggressive knapsack mode — "
            "sector caps are ignored and the allocator brute-forces "
            "integer shares until cash residual ≈ ₹0."
        ),
    )
    if risk_per_trade_pct >= 95:
        st.markdown(
            '<span class="unlocked-pulse">⚠ AGGRESSIVE KNAPSACK UNLOCKED</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="unlock-note">Sector & diversification rails are OFF. '
            'A single high-score stock may absorb the full capital. Residual '
            'cash is filled with the cheapest available share.</div>',
            unsafe_allow_html=True,
        )

    scan_limit = st.slider(
        "Live Scan Limit",
        min_value=10,
        max_value=100,
        value=30,
        step=5,
        help=(
            f"Number of NSE tickers to randomly sample from the {len(NSE_UNIVERSE)}-name "
            "broad universe each run. Smaller = faster + safer from yfinance rate "
            "limits; larger = more coverage. Random sampling rotates exposure "
            "across the whole market over multiple runs."
        ),
    )

    st.markdown("---")
    run_btn = st.button("🚀 Launch Garuda Scan", use_container_width=True)
    show_lottie("scanning", 140)
    st.caption(
        f"Universe: {len(NSE_UNIVERSE)} NSE tickers · "
        "Engine: Hurst + Absorption + Sector-Z + ATR"
    )


# =========================================================================
# Session state bootstrap
# =========================================================================
if "result" not in st.session_state:
    st.session_state["result"] = None
if "ghost" not in st.session_state:
    st.session_state["ghost"] = None


# =========================================================================
# Pipeline trigger
# =========================================================================
if run_btn:
    progress = st.progress(0.0, text="Booting Garuda engine…")

    def _cb(pct: float, msg: str):
        progress.progress(min(max(pct, 0.0), 1.0), text=msg)

    with st.spinner("Running institutional alpha pipeline…"):
        result = run_full_pipeline(
            capital=float(capital),
            risk_profile=RISK_PROFILES[risk_label],
            scan_limit=int(scan_limit),
            risk_per_trade_pct=float(risk_per_trade_pct),
            progress_cb=_cb,
        )
    progress.empty()
    st.session_state["result"] = result
    if result["positions"]:
        mode = "AGGRESSIVE" if result["aggressive_mode"] else "DIVERSIFIED"
        st.success(
            f"[{mode}] Allocated ₹{result['capital_used']:,.0f} of "
            f"₹{result['capital']:,.0f} "
            f"({result['utilisation_pct']:.1f}% utilisation) across "
            f"{len(result['positions'])} positions. "
            f"Scanned {result['signals_scanned']} random tickers, "
            f"{result['signals_passed']} passed the alpha filters."
        )
    else:
        st.warning(
            "No equity passed the institutional filters in this random sample. "
            "Re-run the scan (the universe is shuffled each time) or raise "
            "Max Risk Per Trade and Live Scan Limit."
        )


result = st.session_state["result"]


# =========================================================================
# Tabs
# =========================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Execution Matrix",
    "🧠 Intelligence Terminal & XAI",
    "👻 Ghost-Testing",
    "🛡️ Risk Safeguards",
])


# ---------------------------------------------------------------------------
# TAB 1 — Execution Matrix
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("Garuda-Ops Execution Matrix")
    if not result or not result["positions"]:
        st.info("Configure capital + sliders in the sidebar and press **🚀 Launch Garuda Scan**.")
    else:
        cols = st.columns(4)
        kpis = [
            ("Capital Deployed", f"₹{result['capital_used']:,.0f}", "mint"),
            ("Utilisation",      f"{result['utilisation_pct']:.1f}%", "amber"),
            ("Projected Net P&L",f"₹{result['total_net_profit']:,.0f}",
                "mint" if result['total_net_profit'] >= 0 else "crimson"),
            ("Statutory Fees",   f"₹{result['total_fees']:,.0f}", "amber"),
        ]
        for c, (lbl, val, col) in zip(cols, kpis):
            c.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-label">{lbl}</div>
                    <div class="kpi-value {col}">{val}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("")

        rows = []
        for p in result["positions"]:
            rows.append({
                "Ticker": p.ticker,
                "Action": "BUY",
                "Sector": p.sector,
                "Entry (₹)": round(p.entry_price, 2),
                "Qty": int(p.quantity),
                "Capital (₹)": p.capital_used,
                "Stop (₹)": p.stop_loss,
                "Target (₹)": p.target_price,
                "Hold (Days)": p.expected_holding_days,
                "Fees (₹)": p.total_fees,
                "Net Profit (₹)": p.net_profit,
                "Composite": p.composite_score,
            })
        df = pd.DataFrame(rows)

        badge = '<span class="unlocked-pulse">AGGRESSIVE FILL</span>' if result["aggressive_mode"] \
                else '<span class="buy-pulse">LIVE BUY MATRIX</span>'
        st.markdown(badge, unsafe_allow_html=True)

        st.dataframe(
            df.style.format({
                "Entry (₹)":      "₹{:,.2f}",
                "Capital (₹)":    "₹{:,.2f}",
                "Stop (₹)":       "₹{:,.2f}",
                "Target (₹)":     "₹{:,.2f}",
                "Fees (₹)":       "₹{:,.2f}",
                "Net Profit (₹)": "₹{:,.2f}",
            }),
            use_container_width=True,
            hide_index=True,
            height=440,
        )

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Export Execution Matrix (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"garuda_matrix_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=False,
        )


# ---------------------------------------------------------------------------
# TAB 2 — Intelligence Terminal & XAI
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Intelligence Terminal & Explainable-AI")
    if not result or not result["positions"]:
        st.info("Run a scan first to unlock the intelligence layer.")
    else:
        st.plotly_chart(render_sector_treemap(result["positions"]),
                        use_container_width=True)
        st.plotly_chart(render_projection_heatmap(result["positions"]),
                        use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔬 Per-Position XAI Attribution")
        tickers = [p.ticker for p in result["positions"]]
        chosen = st.selectbox("Select position", tickers, index=0, key="xai_pick")
        active = next(p for p in result["positions"] if p.ticker == chosen)
        st.plotly_chart(render_xai_gauge(active.contributions, chosen),
                        use_container_width=True)

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-label">Composite Alpha Score</div>
                    <div class="kpi-value mint">{active.composite_score:.2f}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_b:
            png = generate_tear_sheet_image(active, active.contributions)
            st.download_button(
                "🖼️ Generate Tear-Sheet (PNG)",
                data=png,
                file_name=f"garuda_tearsheet_{active.ticker.replace('.', '_')}.png",
                mime="image/png",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# TAB 3 — Ghost-Testing
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("Historical Ghost-Testing")
    st.caption(
        "Re-runs the full Garuda stack as-of a past date and grades every "
        "signal against the real subsequent 30-day price action."
    )

    today = datetime.now().date()
    default_dt = today - timedelta(days=45)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        ghost_date = st.date_input(
            "As-of date",
            value=default_dt,
            max_value=today - timedelta(days=10),
            min_value=today - timedelta(days=300),
        )
    with col2:
        ghost_n = st.slider("Top-N signals to grade", 3, 12, 6)
    with col3:
        ghost_universe = st.slider("Ghost universe size", 10, 40, 20, step=5)

    if st.button("⏪ Run Ghost-Test", use_container_width=False):
        with st.spinner("Time-warping the engine…"):
            tester = GhostTester()
            import random as _r
            sample = _r.sample(list(NSE_UNIVERSE.keys()), ghost_universe)
            ghost_res = tester.run(
                as_of=datetime.combine(ghost_date, datetime.min.time()),
                forward_window_days=30,
                universe=sample,
                top_n=ghost_n,
            )
        st.session_state["ghost"] = ghost_res

    gres = st.session_state["ghost"]
    if gres:
        cA, cB, cC, cD = st.columns(4)
        cA.markdown(
            f"""<div class="kpi-card"><div class="kpi-label">Signals Tested</div>
                <div class="kpi-value">{gres['tested']}</div></div>""",
            unsafe_allow_html=True)
        cB.markdown(
            f"""<div class="kpi-card"><div class="kpi-label">Wins</div>
                <div class="kpi-value mint">{gres['wins']}</div></div>""",
            unsafe_allow_html=True)
        cC.markdown(
            f"""<div class="kpi-card"><div class="kpi-label">Losses</div>
                <div class="kpi-value crimson">{gres['losses']}</div></div>""",
            unsafe_allow_html=True)
        cD.markdown(
            f"""<div class="kpi-card"><div class="kpi-label">Accuracy</div>
                <div class="kpi-value amber">{gres['accuracy_pct']:.1f}%</div></div>""",
            unsafe_allow_html=True)

        if gres["trades"]:
            df_g = pd.DataFrame(gres["trades"])
            st.dataframe(df_g, use_container_width=True, hide_index=True)
        else:
            st.warning("No signals qualified on that date. Try an earlier window or larger ghost universe.")


# ---------------------------------------------------------------------------
# TAB 4 — Risk Safeguards
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("Institutional Risk Safeguards")
    if not result:
        st.info("Risk dashboard activates after the first scan.")
    else:
        c1, c2, c3 = st.columns(3)
 