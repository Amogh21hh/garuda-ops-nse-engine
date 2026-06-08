# Garuda-Ops — NSE Quantitative Capital Allocation Engine

> **A production-style quantitative terminal for the Indian National Stock Exchange.** Allocate user-defined INR capital across 420 NSE tickers via integer-knapsack optimisation. Hurst-exponent trend filtering, microstructure absorption scoring, sector Z-score statistical arbitrage, full Indian statutory cost accounting, and an explainable-AI signal attribution layer.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://garuda-ops.streamlit.app)
[![Made with Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Status:** Research and educational tool — **NOT** SEBI-registered investment advice.

---

## 1. What it does

Given a deployable INR capital amount (₹5,000 to ₹10,00,000+) and a risk profile, Garuda-Ops returns a **100%-utilised, integer-share portfolio** across a 420-ticker NSE universe with full risk transparency and statutory fee reconciliation.

| Layer | Method |
|---|---|
| Trend detection | Rolling Hurst Exponent (R/S analysis, windows 8 / 16 / 32) |
| Microstructure | Close-position × log-relative-volume **absorption score** |
| Cross-sectional | 30-day Z-score of stock-vs-sector return spread |
| Volatility regime | 14-day ATR with expansion / contraction detection |
| Capital allocation | Greedy **integer knapsack** with sector concentration caps + aggressive-fill residual sweep |
| Cost engine | STT, GST, SEBI charges, brokerage, stamp duty, exchange, DP |
| Validation | As-of date "Ghost-Tester" backtester with win/loss grading |
| Explainability | Per-position normalised signal feature attribution |

---

## 2. Headline numbers (validated)

- **Universe:** 420 NSE tickers across 26 sectors (Banking 25 · Financial Services 35 · IT 29 · Pharma 33 · FMCG 20 · Auto 25 · Metals 18 · Chemicals 23 · Capital Goods 22 · …)
- **Capital utilisation:** **99.96%** at ₹50,000 input (aggressive mode); **99.4%** at ₹5,000
- **Cost engine accuracy:** every Indian statutory fee accounted for at the share level
- **Backtester:** re-runs the full signal stack as-of any past date and grades against forward 30-day OHLC

---

## 3. Architecture

```
                    ┌────────────────────────────────────┐
                    │   app_garuda_main.py (Streamlit)   │
                    │   sidebar + 4-tab dashboard        │
                    └────────────────────────────────────┘
                                    │ user inputs
                                    ▼
┌────────────────────────┐   ┌────────────────────────┐
│ garuda_config_assets   │──▶│  garuda_quant_engine   │
│ 420 NSE tickers · fees │   │  10-class signal +     │
│ 26-sector map          │   │  integer-knapsack      │
└────────────────────────┘   └────────────────────────┘
                                    │ scored portfolio
                                    ▼
                    ┌────────────────────────────────────┐
                    │  garuda_xai_visualizer.py          │
                    │  Plotly + Pillow tear-sheets       │
                    └────────────────────────────────────┘
```

| File | Role |
|---|---|
| `garuda_config_assets.py` | 420 NSE tickers, sector groups, fee schedules |
| `garuda_quant_engine.py` | 10-class signal pipeline + `GreedyKnapsackAllocator` |
| `garuda_xai_visualizer.py` | Plotly charts + Pillow tear-sheet PNGs |
| `app_garuda_main.py` | Streamlit terminal UI |
| `requirements.txt` | pinned dependencies |

---

## 4. Quant methods (no off-the-shelf indicators)

**Rolling Hurst Exponent (R/S):**
H ≈ 0.5 → random walk · H > 0.55 → trending · H < 0.45 → mean-reverting.
Disqualifies noise stocks before the optimiser ever sees them.

**Absorption score:** `close_position × log_relative_volume`. Captures institutional block buying on the close.

**Sector Z-score stat-arb:** for each stock, `(stock_return − sector_return) / σ_30d`. Mean-reversion candidate when |Z| > 1.5.

**Integer-programming knapsack:** greedy fill by composite score, sector cap = `max_position_weight`, residual sweep buys the cheapest signalled share until cash residual approaches zero.

**Aggressive unlock (≥95% max position):** disables sector caps, softens Hurst threshold by 0.10, softens absorption gate to 0.05. Designed for small-capital deployment (₹5k–₹50k) where strict caps leave too much cash idle.

---

## 5. Install & run locally

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1            # Windows
# source venv/bin/activate              # macOS / Linux

pip install -r requirements.txt
streamlit run app_garuda_main.py
```

The app opens at `http://localhost:8501`.



---

## 6. Compliance

This is an educational research artefact. Outputs are statistical signals, not investment advice. The Indian capital markets are regulated by SEBI; consult a SEBI-registered investment adviser before deploying capital. Past signal performance is not indicative of future results.

---

## 7. License

MIT — see [LICENSE](LICENSE).

---

## 8. Author

**Amogh H. H.** — MSc Business Analytics, University of Essex
[LinkedIn](https://linkedin.com/in/amogh-hh-34129a1b9) · [Portfolio](https://amogh-h-h-portfolio.vercel.app) · amoghmallikarjun0321@gmail.com

