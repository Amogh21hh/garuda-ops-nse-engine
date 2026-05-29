"""garuda_quant_engine.py — Garuda-Ops mastermind brain.

Changes in this revision:
  * Random-sample scan to avoid yfinance rate-limits.
  * Aggressive Knapsack mode when max_position_weight >= 0.95.
  * Per-ticker .info call disabled by default.
"""
from __future__ import annotations
import math, random, time, warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd
try:
    import yfinance as yf
except Exception:
    yf = None
from garuda_config_assets import INDIAN_MARKET_FEES, NSE_UNIVERSE, SECTOR_INDEX_MAP

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class StockSignal:
    ticker: str
    sector: str
    last_price: float
    atr: float
    hurst: float
    absorption: float
    velocity_z: float
    composite_score: float
    target_price: float
    stop_loss: float
    contributions: dict = field(default_factory=dict)


@dataclass
class AllocatedPosition:
    ticker: str
    sector: str
    entry_price: float
    quantity: int
    capital_used: float
    target_price: float
    stop_loss: float
    expected_holding_days: int
    gross_profit: float
    total_fees: float
    net_profit: float
    composite_score: float
    contributions: dict


# ----- 1. Data Fetcher -----
class GarudaDataFetcher:
    def __init__(self, period: str = "6mo", interval: str = "1d", retries: int = 2):
        self.period = period
        self.interval = interval
        self.retries = retries

    def fetch_single(self, ticker: str) -> Optional[pd.DataFrame]:
        if yf is None:
            return None
        for attempt in range(self.retries + 1):
            try:
                df = yf.download(ticker, period=self.period, interval=self.interval,
                                 progress=False, auto_adjust=False, threads=False)
                if df is None or df.empty:
                    time.sleep(0.25 * (attempt + 1))
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna()
                if len(df) >= 40:
                    return df
            except Exception:
                time.sleep(0.4 * (attempt + 1))
        return None

    def fetch_info(self, ticker: str) -> dict:
        if yf is None:
            return {}
        try:
            return yf.Ticker(ticker).info or {}
        except Exception:
            return {}


# ----- 2. Fundamental Credit Filter (off by default) -----
class FundamentalCreditFilter:
    def __init__(self, max_debt_to_equity: float = 3.0, enabled: bool = False):
        self.max_de = max_debt_to_equity
        self.enabled = enabled
        self.fetcher = GarudaDataFetcher()

    def passes(self, ticker: str) -> bool:
        if not self.enabled:
            return True
        info = self.fetcher.fetch_info(ticker)
        if not info:
            return True
        de = info.get("debtToEquity")
        if de is None:
            return True
        try:
            de_val = float(de)
        except (TypeError, ValueError):
            return True
        if de_val > 100:
            de_val /= 100.0
        return de_val <= self.max_de


# ----- 3. Hurst Exponent Filter -----
class FractalEfficiencyFilter:
    WINDOWS = (8, 16, 32)

    @staticmethod
    def _hurst_rs(series: np.ndarray) -> float:
        n = len(series)
        if n < 8:
            return 0.5
        mean = np.mean(series)
        cumulative = np.cumsum(series - mean)
        R = np.max(cumulative) - np.min(cumulative)
        S = np.std(series, ddof=1)
        if S == 0 or R == 0:
            return 0.5
        return math.log(R / S) / math.log(n)

    @classmethod
    def rolling_hurst(cls, prices: pd.Series) -> float:
        log_returns = np.log(prices).diff().dropna().values
        if len(log_returns) < max(cls.WINDOWS):
            return 0.5
        values = []
        for w in cls.WINDOWS:
            h = cls._hurst_rs(log_returns[-w:])
            if not math.isnan(h) and not math.isinf(h):
                values.append(h)
        if not values:
            return 0.5
        return float(np.clip(np.mean(values), 0.0, 1.0))

    @classmethod
    def is_trending(cls, prices: pd.Series, min_h: float = 0.58) -> tuple[bool, float]:
        h = cls.rolling_hurst(prices)
        if 0.45 <= h <= 0.55:
            return False, h
        return h >= min_h, h


# ----- 4. Institutional Absorption -----
class InstitutionalAbsorptionScorer:
    @staticmethod
    def score(df: pd.DataFrame, lookback: int = 20) -> float:
        if len(df) < lookback + 1:
            return 0.0
        recent = df.tail(lookback).copy()
        rng = (recent["High"] - recent["Low"]).replace(0, np.nan)
        close_pos = ((recent["Close"] - recent["Low"]) / rng).fillna(0.5)
        avg_vol = recent["Volume"].rolling(lookback).mean().iloc[-1]
        if pd.isna(avg_vol) or avg_vol <= 0:
            return 0.0
        rel_vol = recent["Volume"] / avg_vol
        log_rel = np.log1p(rel_vol.clip(lower=0))
        per_day = close_pos.values * log_rel.values
        weights = np.linspace(0.5, 1.5, len(per_day))
        return float(np.clip(np.average(per_day, weights=weights), 0.0, 5.0))


# ----- 5. Cross-Sector Z-Velocity -----
class CrossSectorVelocity:
    def __init__(self, fetcher: GarudaDataFetcher):
        self.fetcher = fetcher
        self._cache: dict[str, Optional[pd.DataFrame]] = {}

    def _sector_df(self, sector: str) -> Optional[pd.DataFrame]:
        idx = SECTOR_INDEX_MAP.get(sector, "^NSEI")
        if idx in self._cache:
            return self._cache[idx]
        df = self.fetcher.fetch_single(idx)
        self._cache[idx] = df
        return df

    def z_score(self, stock_df: pd.DataFrame, sector: str, lookback: int = 30) -> float:
        sec_df = self._sector_df(sector)
        if sec_df is None or len(sec_df) < lookback:
            return 0.0
        s_ret = stock_df["Close"].pct_change().dropna().tail(lookback)
        i_ret = sec_df["Close"].pct_change().dropna().tail(lookback)
        joined = pd.concat([s_ret, i_ret], axis=1, join="inner").dropna()
        if len(joined) < 10:
            return 0.0
        spread = joined.iloc[:, 0] - joined.iloc[:, 1]
        mu, sigma = spread.mean(), spread.std(ddof=1)
        if sigma == 0 or pd.isna(sigma):
            return 0.0
        return float(np.clip((spread.iloc[-1] - mu) / sigma, -4.0, 4.0))


# ----- 6. Adaptive ATR Risk Pricing -----
class AdaptiveRiskPricing:
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> float:
        if len(df) < period + 1:
            return 0.0
        high, low, close = df["High"], df["Low"], df["Close"]
        tr = pd.concat([high - low, (high - close.shift()).abs(),
                        (low - close.shift()).abs()], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    @classmethod
    def derive(cls, df: pd.DataFrame, base_target_mult: float, base_stop_mult: float):
        atr_now = cls.atr(df, 14)
        atr_prev = cls.atr(df.iloc[:-5], 14) if len(df) > 25 else atr_now
        expanding = atr_now > atr_prev
        tgt_mult = 3.5 if expanding else max(1.5, base_target_mult * 0.6)
        stp_mult = base_stop_mult * (1.1 if expanding else 0.9)
        last = float(df["Close"].iloc[-1])
        return atr_now, last + atr_now * tgt_mult, last - atr_now * stp_mult


# ----- 7. XAI Explainer -----
class XAIExplainer:
    WEIGHTS = {
        "Hurst Trend Strength": 0.30,
        "Institutional Absorption": 0.30,
        "Sector Mean-Reversion": 0.20,
        "Volatility Regime (ATR)": 0.20,
    }

    @classmethod
    def attribute(cls, hurst, absorption, velocity_z, atr, last_price) -> dict[str, float]:
        h_score = max(0.0, min(1.0, (hurst - 0.50) / 0.40))
        a_score = max(0.0, min(1.0, absorption / 2.5))
        v_score = max(0.0, min(1.0, (-velocity_z + 1.5) / 3.0))
        atr_pct = (atr / last_price) if last_price > 0 else 0.0
        if atr_pct <= 0:
            r_score = 0.0
        elif atr_pct < 0.01:
            r_score = atr_pct / 0.01
        elif atr_pct <= 0.04:
            r_score = 1.0
        else:
            r_score = max(0.0, 1.0 - (atr_pct - 0.04) / 0.06)
        raw = {
            "Hurst Trend Strength":     h_score * cls.WEIGHTS["Hurst Trend Strength"],
            "Institutional Absorption": a_score * cls.WEIGHTS["Institutional Absorption"],
            "Sector Mean-Reversion":    v_score * cls.WEIGHTS["Sector Mean-Reversion"],
            "Volatility Regime (ATR)":  r_score * cls.WEIGHTS["Volatility Regime (ATR)"],
        }
        total = sum(raw.values())
        if total <= 0:
            return {k: 25.0 for k in raw}
        return {k: round(v / total * 100.0, 2) for k, v in raw.items()}

    @staticmethod
    def composite(contributions: dict[str, float]) -> float:
        return float(sum(contributions.values()))


# ----- 8. Greedy Knapsack with Aggressive Override -----
class GreedyKnapsackAllocator:
    AGGRESSIVE_THRESHOLD = 0.95

    def __init__(self, capital: float, max_sector_weight: float = 0.35,
                 max_position_weight: float = 0.25):
        self.capital = float(capital)
        self.max_sector_weight = float(max_sector_weight)
        self.max_position_weight = float(max_position_weight)

    def allocate(self, signals: list[StockSignal], max_positions: int) -> list[dict]:
        if not signals or self.capital <= 0:
            return []
        ranked = sorted(signals, key=lambda s: s.composite_score, reverse=True)
        if self.max_position_weight >= self.AGGRESSIVE_THRESHOLD:
            return self._aggressive_fill(ranked[:max(max_positions, 6)])
        return self._diversified_fill(ranked, max_positions)

    def _aggressive_fill(self, ranked: list[StockSignal]) -> list[dict]:
        remaining = self.capital
        allocations: dict[str, dict] = {}
        # Phase 1: greedy by composite score
        for s in ranked:
            if remaining <= 0:
                break
            if s.last_price <= 0 or s.last_price > remaining:
                continue
            qty = int(remaining // s.last_price)
            if qty <= 0:
                continue
            spend = qty * s.last_price
            allocations[s.ticker] = {"signal": s, "qty": qty, "spend": spend}
            remaining -= spend
        # Phase 2: cheapest-share residual sweep
        guard = 0
        while remaining > 0 and guard < 5000:
            guard += 1
            cheapest = None
            cheapest_price = float("inf")
            for s in ranked:
                if s.last_price <= 0 or s.last_price > remaining:
                    continue
                if s.last_price < cheapest_price:
                    cheapest_price = s.last_price
                    cheapest = s
            if cheapest is None:
                break
            entry = allocations.get(cheapest.ticker)
            if entry is None:
                allocations[cheapest.ticker] = {"signal": cheapest, "qty": 1,
                                                "spend": cheapest.last_price}
            else:
                entry["qty"] += 1
                entry["spend"] += cheapest.last_price
            remaining -= cheapest.last_price
        return list(allocations.values())

    def _diversified_fill(self, ranked: list[StockSignal], max_positions: int) -> list[dict]:
        sector_cap = self.capital * self.max_sector_weight
        position_cap = self.capital * self.max_position_weight
        sector_usage: dict[str, float] = {}
        remaining = self.capital
        allocations: dict[str, dict] = {}
        top = ranked[:max_positions]
        score_sum = sum(max(s.composite_score, 1e-6) for s in top)
        for s in top:
            if s.last_price <= 0 or s.last_price > remaining:
                continue
            seed_budget = self.capital * (s.composite_score / score_sum)
            sector_room = sector_cap - sector_usage.get(s.sector, 0.0)
            budget = min(seed_budget, sector_room, position_cap, remaining)
            if budget < s.last_price:
                continue
            qty = int(budget // s.last_price)
            if qty <= 0:
                continue
            spend = qty * s.last_price
            allocations[s.ticker] = {"signal": s, "qty": qty, "spend": spend}
            sector_usage[s.sector] = sector_usage.get(s.sector, 0.0) + spend
            remaining -= spend
        guard = 0
        while remaining > 0 and guard < 3000:
            guard += 1
            picked = None
            best_score = -1.0
            for s in ranked:
                if s.last_price <= 0 or s.last_price > remaining:
                    continue
                if sector_usage.get(s.sector, 0.0) + s.last_price > sector_cap:
                    continue
                used_pos = allocations.get(s.ticker, {}).get("spend", 0.0)
                if used_pos + s.last_price > position_cap:
                    continue
                if s.composite_score > best_score:
                    best_score = s.composite_score
                    picked = s
            if picked is None:
                break
            entry = allocations.get(picked.ticker)
            if entry is None:
                allocations[picked.ticker] = {"signal": picked, "qty": 1,
                                              "spend": picked.last_price}
            else:
                entry["qty"] += 1
                entry["spend"] += picked.last_price
            sector_usage[picked.sector] = sector_usage.get(picked.sector, 0.0) + picked.last_price
            remaining -= picked.last_price
        return list(allocations.values())


# ----- 9. Profit & Cost Projection -----
class ProfitAndCostProjectionEngine:
    @staticmethod
    def estimate_holding_days(atr, last_price, target) -> int:
        if atr <= 0 or last_price <= 0:
            return 30
        per_day = atr * 0.45
        if per_day <= 0:
            return 30
        return max(2, min(int(math.ceil(abs(target - last_price) / per_day)), 60))

    @staticmethod
    def round_trip_fees(buy_value: float, sell_value: float) -> float:
        f = INDIAN_MARKET_FEES
        turnover = buy_value + sell_value
        brokerage = f["BROKERAGE_FLAT_INR"] * 2
        stt = f["STT_PCT"] * sell_value
        sebi = f["SEBI_PCT"] * turnover
        stamp = f["STAMP_DUTY_PCT"] * buy_value
        exch = f["EXCHANGE_TXN_PCT"] * turnover
        gst = f["GST_PCT"] * (brokerage + sebi + exch)
        return round(brokerage + stt + sebi + stamp + exch + gst + f["DP_CHARGES_INR"], 2)

    @classmethod
    def project(cls, signal: StockSignal, qty: int) -> dict:
        buy_value = qty * signal.last_price
        sell_value = qty * signal.target_price
        gross = sell_value - buy_value
        fees = cls.round_trip_fees(buy_value, sell_value)
        return {
            "buy_value": round(buy_value, 2),
            "sell_value": round(sell_value, 2),
            "gross_profit": round(gross, 2),
            "total_fees": fees,
            "net_profit": round(gross - fees, 2),
            "holding_days": cls.estimate_holding_days(signal.atr, signal.last_price, signal.target_price),
        }


# ----- 10. Ghost Tester -----
class GhostTester:
    def __init__(self, fetcher: Optional[GarudaDataFetcher] = None):
        self.fetcher = fetcher or GarudaDataFetcher(period="1y", interval="1d")

    def _signal_asof(self, ticker, sector, df, velocity) -> Optional[StockSignal]:
        if len(df) < 60:
            return None
        prices = df["Close"]
        passes, h = FractalEfficiencyFilter.is_trending(prices, min_h=0.58)
        if not passes:
            return None
        absorption = InstitutionalAbsorptionScorer.score(df)
        vz = velocity.z_score(df, sector)
        atr, tgt, stp = AdaptiveRiskPricing.derive(df, 2.5, 1.2)
        last = float(prices.iloc[-1])
        contribs = XAIExplainer.attribute(h, absorption, vz, atr, last)
        return StockSignal(ticker=ticker, sector=sector, last_price=last, atr=atr,
                           hurst=h, absorption=absorption, velocity_z=vz,
                           composite_score=XAIExplainer.composite(contribs),
                           target_price=tgt, stop_loss=stp, contributions=contribs)

    def run(self, as_of: datetime, forward_window_days: int = 30,
            universe: Optional[list[str]] = None, top_n: int = 8) -> dict:
        universe = universe or random.sample(list(NSE_UNIVERSE.keys()), 25)
        velocity = CrossSectorVelocity(self.fetcher)
        candidates = []
        for tkr in universe:
            full = self.fetcher.fetch_single(tkr)
            if full is None:
                continue
            full.index = pd.to_datetime(full.index)
            past_df = full[full.index <= pd.Timestamp(as_of)]
            fwd = full[full.index > pd.Timestamp(as_of)].head(forward_window_days)
            if len(past_df) < 60 or len(fwd) < 5:
                continue
            sig = self._signal_asof(tkr, NSE_UNIVERSE.get(tkr, "Misc"), past_df, velocity)
            if sig is None:
                continue
            candidates.append((sig, fwd))
        if not candidates:
            return {"tested": 0, "wins": 0, "losses": 0, "accuracy_pct": 0.0, "trades": []}
        candidates.sort(key=lambda x: x[0].composite_score, reverse=True)
        picks = candidates[:top_n]
        trades, wins, losses = [], 0, 0
        for sig, fwd in picks:
            hit_tgt = bool((fwd["High"] >= sig.target_price).any())
            hit_stp = bool((fwd["Low"] <= sig.stop_loss).any())
            outcome = "FLAT"
            if hit_tgt and not hit_stp:
                outcome = "WIN"; wins += 1
            elif hit_stp and not hit_tgt:
                outcome = "LOSS"; losses += 1
            elif hit_tgt and hit_stp:
                t_first = fwd.index[(fwd["High"] >= sig.target_price)][0]
                s_first = fwd.index[(fwd["Low"] <= sig.stop_loss)][0]
                if t_first <= s_first:
                    outcome = "WIN"; wins += 1
                else:
                    outcome = "LOSS"; losses += 1
            else:
                ret = (fwd["Close"].iloc[-1] - sig.last_price) / sig.last_price
                if ret > 0.02:
                    outcome = "WIN"; wins += 1
                elif ret < -0.02:
                    outcome = "LOSS"; losses += 1
            trades.append({"Ticker": sig.ticker, "Sector": sig.sector,
                           "Entry": round(sig.last_price, 2),
                           "Target": round(sig.target_price, 2),
                           "Stop": round(sig.stop_loss, 2), "Outcome": outcome,
                           "Composite": round(sig.composite_score, 2)})
        total = wins + losses
        acc = (wins / total * 100.0) if total > 0 else 0.0
        return {"tested": len(picks), "wins": wins, "losses": losses,
                "accuracy_pct": round(acc, 2), "trades": trades}


# ----- Master pipeline orchestrator -----
def run_full_pipeline(capital: float, risk_profile: dict, scan_limit: int = 30,
                     risk_per_trade_pct: float = 25.0, progress_cb=None) -> dict:
    fetcher = GarudaDataFetcher(period="6mo", interval="1d")
    velocity = CrossSectorVelocity(fetcher)
    full_universe = list(NSE_UNIVERSE.keys())
    n = max(5, min(int(scan_limit), len(full_universe)))
    tickers = random.sample(full_universe, n)
    risk_per_trade_pct = float(max(1.0, min(100.0, risk_per_trade_pct)))
    aggressive = risk_per_trade_pct >= 95.0
    min_h = max(0.50, risk_profile["min_hurst"] - (0.10 if aggressive else 0.0))
    min_absorption = 0.05 if aggressive else 0.15

    signals: list[StockSignal] = []
    for i, tkr in enumerate(tickers):
        if progress_cb:
            progress_cb(i / len(tickers), f"Scanning {tkr}")
        df = fetcher.fetch_single(tkr)
        if df is None or len(df) < 60:
            continue
        prices = df["Close"]
        passes_trend, h = FractalEfficiencyFilter.is_trending(prices, min_h=min_h)
        if not passes_trend:
            continue
        absorption = InstitutionalAbsorptionScorer.score(df)
        if absorption < min_absorption:
            continue
        vz = velocity.z_score(df, NSE_UNIVERSE[tkr])
        atr, target, stop = AdaptiveRiskPricing.derive(
            df, risk_profile["atr_target_mult"], risk_profile["atr_stop_mult"])
        last = float(prices.iloc[-1])
        if last <= 0 or atr <= 0:
            continue
        contribs = XAIExplainer.attribute(h, absorption, vz, atr, last)
        signals.append(StockSignal(
            ticker=tkr, sector=NSE_UNIVERSE[tkr], last_price=last, atr=atr,
            hurst=h, absorption=absorption, velocity_z=vz,
            composite_score=XAIExplainer.composite(contribs),
            target_price=target, stop_loss=stop, contributions=contribs))

    if progress_cb:
        progress_cb(0.95, "Optimising capital allocation")

    allocator = GreedyKnapsackAllocator(
        capital=capital,
        max_sector_weight=risk_profile["max_sector_weight"],
        max_position_weight=risk_per_trade_pct / 100.0)
    raw_alloc = allocator.allocate(signals, max_positions=risk_profile["max_positions"])

    positions: list[AllocatedPosition] = []
    total_used = total_fees = total_net = 0.0
    for entry in raw_alloc:
        sig = entry["signal"]
        qty = entry["qty"]
        proj = ProfitAndCostProjectionEngine.project(sig, qty)
        positions.append(AllocatedPosition(
            ticker=sig.ticker, sector=sig.sector, entry_price=sig.last_price,
            quantity=qty, capital_used=round(proj["buy_value"], 2),
            target_price=round(sig.target_price, 2), stop_loss=round(sig.stop_loss, 2),
            expected_holding_days=proj["holding_days"],
            gross_profit=proj["gross_profit"], total_fees=proj["total_fees"],
            net_profit=proj["net_profit"],
            composite_score=round(sig.composite_score, 2),
            contributions=sig.contributions))
        total_used += proj["buy_value"]
        total_fees += proj["total_fees"]
        total_net += proj["net_profit"]

    if progress_cb:
        progress_cb(1.0, "Complete")

    return {
        "capital": capital,
        "capital_used": round(total_used, 2),
        "capital_unused": round(capital - total_used, 2),
        "utilisation_pct": round((total_used / capital * 100.0) if capital > 0 else 0.0, 2),
        "total_fees": round(total_fees, 2),
        "total_net_profit": round(total_net, 2),
        "positions": positions,
        "signals_scanned": len(tickers),
        "signals_passed": len(signals),
        "aggressive_mode": aggressive,
        "risk_per_trade_pct": risk_per_trade_pct,
        "scanned_tickers": tickers,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
