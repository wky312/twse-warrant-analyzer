"""Streamlit UI for 台股權證分析（情境模擬）."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from twse_warrant import analyze
from twse_warrant.analyzers.pricing import fair_warrant_price, sensitivity_table
from twse_warrant.analyzers.scenario import ScenarioInputs, evaluate_scenarios
from twse_warrant.fetchers.yuanta import YuantaFetcher
from twse_warrant.models import AnalysisResult, Warrant
from twse_warrant.utils.tick import adjacent_ticks, round_to_tick, tick_size


st.set_page_config(page_title="台股權證分析", layout="wide", page_icon="📈")


# ============================================================
# Design tokens — Modern Financial SaaS (Geist + 台股紅漲綠跌)
# 來源：web/styles.css（Claude Design hand-off）
# ============================================================
_DESIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@500;600;700&display=swap');

:root {
  --bg: #fafaf9;
  --surface: #ffffff;
  --surface-2: #f6f6f4;
  --ink-1: #0a0a0a;
  --ink-2: #404040;
  --ink-3: #737373;
  --ink-4: #a3a3a3;
  --line-1: #ececea;
  --line-2: #e3e2df;
  --brand: #1d2540;
  --accent: #ff5630;
  --accent-hover: #ee4a23;
  --up: #d92d20;
  --up-bg: #fef2f0;
  --up-bg-2: #fde2dd;
  --up-line: #f8b7ac;
  --down: #079455;
  --down-bg: #effaf3;
  --down-bg-2: #d1f4dd;
  --r-md: 8px;
  --r-lg: 12px;
}

/* App shell */
html, body, .stApp {
  background: var(--bg) !important;
  font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Noto Sans TC', sans-serif !important;
  color: var(--ink-1);
}
[data-testid="stHeader"] {
  background: rgba(255,255,255,0.85) !important;
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--line-1);
}
[data-testid="stMainBlockContainer"] {
  max-width: 1440px;
  padding-top: 24px !important;
  padding-left: 32px !important;
  padding-right: 32px !important;
}

/* Headings */
h1, h2, h3, h4, h5 {
  font-family: 'Geist', sans-serif !important;
  letter-spacing: -0.01em;
  color: var(--ink-1);
}
h1 { font-size: 26px !important; font-weight: 600 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 20px !important; font-weight: 600 !important; }
h3 { font-size: 17px !important; font-weight: 600 !important; }

/* Inputs */
input, textarea,
[data-testid="stTextInput"] input,
[data-testid="stNumberInputField"] {
  font-family: 'Geist Mono', monospace !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  color: var(--ink-1) !important;
}
[data-testid="stTextInput"] > div > div,
[data-testid="stNumberInputContainer"],
[data-testid="stDateInput"] > div > div,
[data-testid="stSelectbox"] > div > div {
  border: 1px solid var(--line-2) !important;
  border-radius: var(--r-md) !important;
  background: var(--surface) !important;
}

/* Widget label uppercase tracking */
[data-testid="stWidgetLabel"] p {
  font-size: 11.5px !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-3) !important;
  font-weight: 500 !important;
}

/* Primary button (CTA) */
.stButton button[kind="primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: white !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  border-radius: var(--r-md) !important;
  height: 42px !important;
  box-shadow: 0 1px 0 rgba(0,0,0,.04), inset 0 1px 0 rgba(255,255,255,.18) !important;
}
.stButton button[kind="primary"]:hover {
  background: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
}

/* Default Streamlit metric (used in calculator output) */
[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line-1);
  border-radius: var(--r-lg);
  padding: 14px 18px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}
[data-testid="stMetricLabel"] p {
  color: var(--ink-3) !important;
  font-size: 11.5px !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 500;
}
[data-testid="stMetricValue"] {
  font-family: 'Geist Mono', monospace !important;
  font-feature-settings: 'tnum';
  font-size: 26px !important;
  font-weight: 600 !important;
  color: var(--ink-1) !important;
  letter-spacing: -0.02em;
}

/* Alert pills */
[data-testid="stAlertContainer"] {
  border-radius: var(--r-md) !important;
  font-size: 13px !important;
  padding: 10px 14px !important;
  border: 1px solid var(--line-1);
}
[data-testid="stAlertContentSuccess"] {
  background: var(--down-bg) !important;
  color: var(--down) !important;
  border-color: var(--down-line);
}

/* Expander */
[data-testid="stExpander"] {
  border-radius: var(--r-md);
  border: 1px solid var(--line-1) !important;
  background: var(--surface);
}
[data-testid="stExpander"] summary {
  font-weight: 500;
  color: var(--ink-1);
}

/* DataFrame */
[data-testid="stDataFrame"] {
  border: 1px solid var(--line-1);
  border-radius: var(--r-md);
  overflow: hidden;
}

/* Custom topbar */
.custom-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 16px;
  border-bottom: 1px solid var(--line-1);
  margin-bottom: 24px;
}
.custom-topbar .brand {
  display: flex; align-items: center; gap: 10px;
  font-family: 'Geist', sans-serif;
}
.custom-topbar .brand-logo {
  width: 28px; height: 28px;
  border-radius: 7px;
  background: linear-gradient(135deg, #1d2540 0%, #2a3658 100%);
  display: grid; place-items: center;
  color: white; font-size: 14px;
}
.custom-topbar .brand-name {
  font-size: 15px; font-weight: 600; letter-spacing: -0.01em;
}
.custom-topbar .brand-name .sub {
  color: var(--ink-3); font-weight: 400; margin-left: 8px;
  font-size: 13px; letter-spacing: 0;
}
.custom-topbar .topbar-right {
  display: flex; align-items: center; gap: 16px;
  color: var(--ink-3); font-size: 12.5px;
}
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 999px;
  background: var(--down-bg); color: var(--down);
  font-weight: 500; font-size: 12px;
}
.status-pill .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--down);
  box-shadow: 0 0 0 3px rgba(7,148,85,0.15);
}

/* Custom KPI cards (replaces st.metric for KPI row) */
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--line-1);
  border-radius: var(--r-lg);
  padding: 16px 18px 14px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}
.kpi-card.accent {
  background: linear-gradient(180deg, #fef6f3 0%, #ffffff 60%);
  border-color: #ffd9ce;
}
.kpi-card .kpi-label {
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-3);
  font-weight: 500;
  margin-bottom: 6px;
}
.kpi-card .kpi-value {
  font-family: 'Geist Mono', monospace;
  font-feature-settings: 'tnum';
  font-size: 28px;
  font-weight: 600;
  color: var(--ink-1);
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.kpi-card.accent .kpi-value { color: var(--up); }
.kpi-card .kpi-meta {
  font-size: 12px;
  color: var(--ink-3);
  margin-top: 4px;
}

/* Top 3 podium cards */
.podium-card {
  background: var(--surface);
  border: 1px solid var(--line-1);
  border-radius: var(--r-lg);
  padding: 18px 18px 14px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}
.podium-card.rank-1 {
  background: linear-gradient(180deg, #fff8f5 0%, #ffffff 50%);
  border-color: var(--up-line);
}
.podium-ribbon {
  height: 4px; position: absolute; top: 0; left: 0; right: 0;
}
.podium-ribbon.rank-1 { background: linear-gradient(90deg, #d92d20, #f8b7ac); }
.podium-ribbon.rank-2 { background: linear-gradient(90deg, #737373, #d4d3cf); }
.podium-ribbon.rank-3 { background: linear-gradient(90deg, #b54708, #f8d3a3); }
.podium-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px;
}
.podium-rank {
  display: inline-grid; place-items: center;
  width: 22px; height: 22px;
  border-radius: 6px;
  font-family: 'Geist Mono', monospace;
  font-size: 11.5px; font-weight: 600;
  color: white;
}
.podium-rank.rank-1 { background: var(--up); }
.podium-rank.rank-2 { background: #737373; }
.podium-rank.rank-3 { background: #b54708; }
.podium-rank-label {
  font-size: 11px; color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.podium-ret {
  font-family: 'Geist Mono', monospace;
  font-feature-settings: 'tnum';
  color: var(--up);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  margin-bottom: 8px;
}
.podium-card.rank-1 .podium-ret { font-size: 36px; }
.podium-card.rank-2 .podium-ret,
.podium-card.rank-3 .podium-ret { font-size: 28px; }
.podium-code {
  font-family: 'Geist Mono', monospace;
  font-size: 16px; font-weight: 600;
  color: var(--ink-1);
}
.podium-name {
  font-size: 13px; color: var(--ink-2); margin-bottom: 12px;
}
.podium-kvs {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px 14px;
  padding: 10px 0;
  border-top: 1px solid var(--line-1);
  border-bottom: 1px solid var(--line-1);
  margin-bottom: 10px;
}
.podium-kvs .kv {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 12px;
}
.podium-kvs .kv .k { color: var(--ink-3); }
.podium-kvs .kv .v {
  font-family: 'Geist Mono', monospace;
  font-feature-settings: 'tnum';
  color: var(--ink-1); font-weight: 500;
}
.podium-warns {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;
}
.podium-warns .w {
  background: var(--down-bg);
  border: 1px solid var(--down-line);
  border-radius: 6px;
  padding: 6px 8px;
  text-align: center;
}
.podium-warns .w .label {
  display: block;
  font-size: 10.5px; color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.podium-warns .w .val {
  font-family: 'Geist Mono', monospace;
  font-feature-settings: 'tnum';
  font-size: 13px; font-weight: 600;
  color: var(--down);
}

/* Page heading */
.page-head {
  padding: 4px 0 16px;
}
.page-head h1 {
  font-size: 26px !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em !important;
  margin: 0 0 4px !important;
}
.page-head .page-sub {
  color: var(--ink-3);
  font-size: 13.5px;
  margin: 0;
}
</style>
"""

st.markdown(_DESIGN_CSS, unsafe_allow_html=True)

# Custom top bar
st.markdown(
    """
    <div class="custom-topbar">
      <div class="brand">
        <div class="brand-logo">📈</div>
        <span class="brand-name">台股權證分析<span class="sub">Warrant Analyzer</span></span>
      </div>
      <div class="topbar-right">
        <span class="status-pill"><span class="dot"></span>市場開盤</span>
        <span>資料來源 yuanta</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="page-head">
      <h1>情境分析 — 找尋能在目標日獲利的權證</h1>
      <p class="page-sub">輸入標的、目標價與日期，工具回傳「在這個情境下哪些權證能獲利」的排序，並提供 Black-Scholes 合理價計算機輔助下單。</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- 主畫面輸入區 ---
input_cols = st.columns([1.2, 1, 0.8, 1.2, 1.3])
with input_cols[0]:
    symbol = st.text_input("標的股票代碼", value="2330", help="例：2330（台積電）、2454（聯發科）")
with input_cols[1]:
    direction_label = st.radio("方向", ["認購", "認售"], horizontal=True)
    direction = "call" if direction_label == "認購" else "put"
with input_cols[2]:
    top_n = st.slider("Top N", 3, 10, 5)
with input_cols[3]:
    scenario_target = st.number_input(
        "目標標的價",
        min_value=1.0, value=2800.0, step=10.0,
        help="您預期標的會到達的價格",
    )
with input_cols[4]:
    today = datetime.now().date()
    scenario_target_date = st.date_input(
        "目標達成日期",
        value=today + timedelta(days=60),
        min_value=today + timedelta(days=1),
        max_value=today + timedelta(days=365),
    )

scenario_days = (scenario_target_date - today).days
st.caption(f"距今 **{scenario_days}** 個日曆日　|　資料來源：元大權證網")
run = st.button("🔍 開始分析", type="primary", use_container_width=True)


# --- helpers ---
def warrant_to_row(w: Warrant) -> dict:
    return {
        "權證代碼": w.symbol,
        "權證名稱": w.name,
        "認購售": "認購" if w.direction == "call" else "認售",
        "成交價": w.last_price,
        "漲跌": w.change,
        "漲跌幅%": w.change_pct,
        "成交量": w.volume,
        "履約價": w.strike,
        "行使比例": w.exercise_ratio,
        "剩餘天數": w.days_to_expiry,
        "價內外%": w.moneyness_pct,
        "買賣價差比%": w.bid_ask_spread_pct,
        "實質槓桿": w.leverage,
        "成交價隱波%": w.iv_mid,
        "等效Δ": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else None,
        "流通在外比例%": w.outstanding_pct,
    }


def render_basic_info(w: Warrant) -> None:
    cols = st.columns(2)
    left = {
        "上市日期": w.issue_date,
        "最後交易日": w.last_trade_date,
        "到期日期": w.maturity_date,
        "發行型態": "歐式" + ("認購" if w.direction == "call" else "認售"),
        "最新發行張數": f"{w.issued_units:,}" if w.issued_units else "-",
        "流通在外張數/比例": f"{w.outstanding_units} / {w.outstanding_pct:.2f}%" if w.outstanding_pct else "-",
        "最新履約價": w.strike,
        "最新行使比例": w.exercise_ratio,
    }
    right = {
        "買價隱波": f"{w.iv_buy:.2f}%" if w.iv_buy else "-",
        "賣價隱波": f"{w.iv_sell:.2f}%" if w.iv_sell else "-",
        "原始 Delta (per unit)": w.delta,
        "等效 Delta (教科書 0~1)": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else "-",
        "Theta": w.theta,
        "剩餘天數": w.days_to_expiry,
        "價內外程度": f"{w.moneyness_pct:.2f}% ({'價內' if (w.moneyness_pct or 0)>0 else '價外'})" if w.moneyness_pct is not None else "-",
        "實質槓桿": w.leverage,
        "買賣價差比": f"{w.bid_ask_spread_pct:.2f}%" if w.bid_ask_spread_pct else "-",
    }
    with cols[0]:
        for k, v in left.items():
            st.text(f"{k:<10} {v}")
    with cols[1]:
        for k, v in right.items():
            st.text(f"{k:<10} {v}")


# --- 執行控制 ---
if run:
    st.session_state["has_run_analysis"] = True
has_run = st.session_state.get("has_run_analysis", False)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_analyze(symbol: str, direction: str, top_n: int) -> AnalysisResult:
    return analyze(
        underlying=symbol, direction=direction,
        profiles=("stable", "aggressive"),
        fetchers=[YuantaFetcher()], top_n=top_n,
    )


# 只有按過分析按鈕才會跑後端
result: AnalysisResult | None = None
if has_run:
    with st.spinner(f"抓取 {symbol} 權證並分析..."):
        try:
            result = _cached_analyze(symbol, direction, top_n)
        except Exception as e:
            st.error(f"分析失敗：{e}")
            st.stop()
    st.session_state["result_candidates"] = result.candidates


# --- 🧮 合理價計算機（永遠可用，分析前後都能算）---
def _render_calculator(candidates: list[Warrant]) -> None:
    """合理價計算機 UI。candidates 為空時走「手動輸入」模式."""
    has_cands = bool(candidates)
    mode = "從候選清單選"
    if has_cands:
        mode = st.radio(
            "輸入模式",
            ["從候選清單選", "手動輸入"],
            horizontal=True, key="calc_mode",
            help="從候選清單選 = 用剛抓到的權證；手動輸入 = 自行輸入合約條件試算",
        )
    else:
        st.caption("📝 手動輸入模式（按上方「🔍 開始分析」可改用候選清單）")
        mode = "手動輸入"

    sel_w: Warrant | None = None
    if mode == "從候選清單選" and has_cands:
        labels = [f"{w.symbol} {w.name}" for w in candidates]
        idx = st.selectbox(
            "選擇權證",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key="calc_warrant_idx",
        )
        sel_w = candidates[idx]
        if sel_w.strike and sel_w.moneyness_pct is not None:
            if sel_w.direction == "call":
                default_spot = sel_w.strike * (1 + sel_w.moneyness_pct / 100.0)
            else:
                default_spot = sel_w.strike * (1 - sel_w.moneyness_pct / 100.0)
        else:
            default_spot = float(sel_w.strike) if sel_w.strike else 100.0
        default_iv = sel_w.iv_mid if sel_w.iv_mid else 30.0
        default_days = sel_w.days_to_expiry or 60
    else:
        # 手動輸入 — 組合 synthetic Warrant
        m_row1 = st.columns(3)
        with m_row1[0]:
            mdir_label = st.radio(
                "方向", ["認購", "認售"], horizontal=True, key="m_dir",
            )
            mdir = "call" if mdir_label == "認購" else "put"
        with m_row1[1]:
            mstrike = st.number_input(
                "履約價", min_value=0.01, value=2300.0, step=1.0,
                key="m_strike",
            )
        with m_row1[2]:
            mratio = st.number_input(
                "行使比例", min_value=0.0001, value=0.005, step=0.001,
                format="%.4f", key="m_ratio",
                help="例：台積電權證常見 0.003 ~ 0.008",
            )
        m_row2 = st.columns(3)
        with m_row2[0]:
            mdays = int(st.number_input(
                "剩餘天數", min_value=1, value=60, step=1, key="m_days",
            ))
        with m_row2[1]:
            mmarket = st.number_input(
                "權證市價（可選，算偏差用）",
                min_value=0.0, value=0.0, step=0.01, key="m_market",
                help="0 = 不算偏差",
            )
        with m_row2[2]:
            default_iv = st.number_input(
                "IV %（預設值）", min_value=5.0, max_value=200.0,
                value=40.0, step=0.5, key="m_iv_default",
                help="下方 slider 微調用",
            )
        sel_w = Warrant(
            symbol="MANUAL", name="手動輸入",
            underlying_symbol=symbol or "?",
            direction=mdir,
            strike=mstrike, exercise_ratio=mratio,
            days_to_expiry=mdays,
            iv_buy=default_iv, iv_sell=default_iv,
            last_price=mmarket if mmarket > 0 else None,
        )
        default_spot = mstrike
        default_days = mdays

    # ── 共用計算區（spot / IV / 利率 / 股息） ──
    spot_tick = tick_size(default_spot)
    cc = st.columns(3)
    with cc[0]:
        spot = st.number_input(
            "現在標的股價", min_value=0.01,
            value=float(round_to_tick(default_spot, "nearest")),
            step=float(spot_tick),
            help=f"標的 tick={spot_tick}",
            key="calc_spot",
        )
    with cc[1]:
        iv_pct = st.slider(
            "隱含波動度 IV %", 5.0, 200.0,
            float(default_iv), step=0.5, key="calc_iv",
        )
    with cc[2]:
        spot_step = st.number_input(
            "敏感度表步長（元）",
            min_value=float(spot_tick), value=float(spot_tick),
            step=float(spot_tick), key="calc_step",
        )

    cc2 = st.columns(2)
    with cc2[0]:
        r_pct = st.number_input(
            "無風險利率 %", 0.0, 10.0, 2.0, step=0.25, key="calc_r",
        )
    with cc2[1]:
        q_pct = st.number_input(
            "股息率 %", 0.0, 10.0, 0.0, step=0.25, key="calc_q",
            help="台積電約 1.8%",
        )

    res = fair_warrant_price(
        sel_w, spot=spot, iv_pct=iv_pct,
        r=r_pct / 100.0, q=q_pct / 100.0,
    )
    if res is None:
        st.warning("缺資料（履約價/IV/天數）無法計算")
        return

    tick_down, tick_up = adjacent_ticks(res.fair_price)
    mcols = st.columns(3)
    mcols[0].metric(
        "BS 合理價",
        f"{round_to_tick(res.fair_price, 'nearest'):.2f}",
        help=f"理論值 {res.fair_price:.4f}",
    )
    mcols[1].metric("📥 買進可掛", f"{tick_down:.2f}")
    mcols[2].metric("📤 賣出可掛", f"{tick_up:.2f}")

    if res.market_price and res.deviation_pct is not None:
        emoji = "🟢" if res.deviation_pct >= 0 else "🔴"
        direction_word = "便宜" if res.deviation_pct >= 0 else "偏貴"
        st.caption(
            f"市價 {res.market_price} | 偏差 {emoji}{res.deviation_pct:+.1f}% "
            f"（市價相對合理價{direction_word}）"
        )
    st.caption(
        f"內含值 {res.intrinsic:.3f} + 時間價值 {res.time_value:.3f}"
        f"　|　到期 {res.days_to_expiry} 天"
    )

    steps = [
        -3 * spot_step, -2 * spot_step, -spot_step,
        0.0,
        spot_step, 2 * spot_step, 3 * spot_step,
    ]
    sens = sensitivity_table(
        sel_w, spot, steps,
        iv_pct=iv_pct, r=r_pct / 100.0, q=q_pct / 100.0,
    )
    sens_rows = []
    for ds, (s, p) in zip(steps, sens):
        if p is None:
            sens_rows.append({
                "股價變動": f"{ds:+.1f}", "標的價": f"{s:.1f}",
                "合理價": "-", "買進掛": "-", "賣出掛": "-",
            })
        else:
            bd, bu = adjacent_ticks(p)
            sens_rows.append({
                "股價變動": f"{ds:+.1f}",
                "標的價": f"{round_to_tick(s, 'nearest'):.1f}",
                "合理價": f"{round_to_tick(p, 'nearest'):.2f}",
                "買進掛": f"{bd:.2f}",
                "賣出掛": f"{bu:.2f}",
            })
    sens_df = pd.DataFrame(sens_rows)
    st.dataframe(sens_df, hide_index=True, use_container_width=True)


with st.expander("🧮 合理價計算機（BS）", expanded=not has_run):
    _render_calculator(list(result.candidates) if result else [])


# --- 沒按分析就停在這 ---
if not has_run or result is None:
    st.info("👆 想看完整分析？輸入標的、方向、目標價/日期 → 點上方「🔍 開始分析」")
    st.stop()


st.success(f"資料來源：{result.fetch_source}　|　原始候選：{result.raw_count} 檔")
for note in result.notes:
    st.info(note)


# --- 反推現價 ---
spot_now: float | None = None
for w in result.candidates:
    if w.strike and w.moneyness_pct is not None and w.exercise_ratio:
        if w.direction == "call":
            spot_now = w.strike * (1 + w.moneyness_pct / 100.0)
        else:
            spot_now = w.strike * (1 - w.moneyness_pct / 100.0)
        break


# --- 頂部 KPI 卡（design tokens）---
def _kpi_card(label: str, value: str, meta: str = "", accent: bool = False) -> str:
    cls = "kpi-card accent" if accent else "kpi-card"
    return (
        f'<div class="{cls}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-meta">{meta}</div>'
        f'</div>'
    )


if spot_now is not None:
    pct = (float(scenario_target) / spot_now - 1) * 100.0
    target_diff = float(scenario_target) - spot_now
    kpi_cols = st.columns(4)
    kpi_cols[0].markdown(
        _kpi_card("反推標的現價", f"{spot_now:.1f}", "由候選反推"),
        unsafe_allow_html=True,
    )
    kpi_cols[1].markdown(
        _kpi_card(
            "目標價",
            f"NT$ {scenario_target:,.0f}",
            f"{scenario_target_date.strftime('%Y-%m-%d')} 達成",
        ),
        unsafe_allow_html=True,
    )
    kpi_cols[2].markdown(
        _kpi_card(
            "預期漲跌幅",
            f"{pct:+.1f}%",
            f"距現價 {target_diff:+.0f} 點　|　{scenario_days} 天",
            accent=True,
        ),
        unsafe_allow_html=True,
    )
    kpi_cols[3].markdown(
        _kpi_card(
            "候選池",
            f"{result.raw_count:,}",
            f"硬過濾後 {len(result.candidates)} 檔",
        ),
        unsafe_allow_html=True,
    )

    if direction == "call" and pct < 0:
        st.warning(
            f"⚠️ 目標價 {scenario_target:.0f} 低於反推現價 {spot_now:.1f}（{pct:+.1f}%）— 您是否想改選「認售」？"
        )
    elif direction == "put" and pct > 0:
        st.warning(
            f"⚠️ 目標價 {scenario_target:.0f} 高於反推現價 {spot_now:.1f}（{pct:+.1f}%）— 您是否想改選「認購」？"
        )


# --- column config ---
PINNED_COLUMNS = {
    "權證代碼": st.column_config.TextColumn("權證代碼", pinned=True),
    "權證名稱": st.column_config.TextColumn("權證名稱", pinned=True),
}
SCENARIO_COLUMN_CONFIG = {
    **PINNED_COLUMNS,
    "等效Δ": st.column_config.NumberColumn("等效Δ", help="教科書 0~1 Delta（已除以行使比例）；認購正、認售負"),
    "IV%": st.column_config.NumberColumn("IV%", help="隱含波動度（買價/賣價隱波取中位）；越高代表權證越貴"),
    "槓桿": st.column_config.NumberColumn("槓桿", help="實質槓桿"),
    "履約價": st.column_config.NumberColumn("履約價", help="權證的履約價"),
    "價內外%": st.column_config.NumberColumn("價內外%", help="目前價內(+) 或價外(-) 的百分比"),
    "天期": st.column_config.NumberColumn("天期", help="權證剩餘日曆天數"),
    "損益兩平": st.column_config.NumberColumn("損益兩平", help="標的需漲(call)/跌(put)到此價才回本"),
    "達標權證價": st.column_config.NumberColumn("達標權證價", help="若達目標日標的到目標價，預期權證的價格"),
    "達標報酬%": st.column_config.NumberColumn("達標報酬%", help="達標時相對現價的報酬"),
    "平盤報酬%": st.column_config.NumberColumn("平盤報酬%", help="若標的不動到目標日，預期權證價變化"),
    "跌5%報酬%": st.column_config.NumberColumn("跌5%報酬%", help="若標的下跌 5% 到目標日的報酬"),
    "跌10%報酬%": st.column_config.NumberColumn("跌10%報酬%", help="若標的下跌 10% 到目標日的報酬"),
}


# --- 情境模擬（一律執行）---
if result.candidates and spot_now is not None:
    st.divider()
    st.subheader(
        f"🎯 情境模擬：到 {scenario_target_date.strftime('%Y-%m-%d')} 達 {scenario_target:.0f} "
        f"（距今 {scenario_days} 日）"
    )

    scen_inputs = ScenarioInputs(
        target_price=float(scenario_target),
        days_to_target=int(scenario_days),
        spot_now=spot_now,
        risk_drops_pct=(0.0, -5.0, -10.0),
    )
    scen_batch = evaluate_scenarios(
        result.candidates, scen_inputs,
        require_alive_at_target=True,
        require_profit_at_target=True,
        min_volume=100, max_spread_pct=2.5,
    )
    scen_results = scen_batch.results

    ex_msg_parts = []
    if scen_batch.excluded_too_short:
        ex_msg_parts.append(f"到期早於目標日 **{scen_batch.excluded_too_short}** 檔")
    if scen_batch.excluded_low_volume:
        ex_msg_parts.append(f"成交量不足 {scen_batch.excluded_low_volume} 檔")
    if scen_batch.excluded_wide_spread:
        ex_msg_parts.append(f"價差過寬 {scen_batch.excluded_wide_spread} 檔")
    if scen_batch.excluded_no_profit:
        ex_msg_parts.append(f"達標仍虧損 {scen_batch.excluded_no_profit} 檔")
    if ex_msg_parts:
        st.caption("已過濾：" + "　|　".join(ex_msg_parts))

    if not scen_results:
        st.warning("沒有權證在這個情境下能獲利（過濾後無候選）。試著放寬目標、延長日期。")
    else:
        st.success(f"✅ 通過情境過濾：{len(scen_results)} 檔　|　按達標報酬率排序")

        scen_rows = []
        for r in scen_results[:20]:
            w = r.warrant
            scen_rows.append({
                "權證代碼": w.symbol,
                "權證名稱": w.name,
                "成交價": w.last_price,
                "等效Δ": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else None,
                "IV%": round(w.iv_mid or 0, 1),
                "槓桿": w.leverage,
                "履約價": w.strike,
                "行使比例": round(w.exercise_ratio, 4) if w.exercise_ratio is not None else None,
                "價內外%": round(w.moneyness_pct, 1) if w.moneyness_pct is not None else None,
                "天期": w.days_to_expiry,
                "成交量(張)": w.volume,
                "損益兩平": round(r.breakeven or 0, 0),
                "達標權證價": round(r.expected_warrant_price or 0, 2),
                "達標報酬%": round(r.expected_return_pct or 0, 1),
                "平盤報酬%": round(r.risk_returns.get(0.0, 0) or 0, 1),
                "跌5%報酬%": round(r.risk_returns.get(-5.0, 0) or 0, 1),
                "跌10%報酬%": round(r.risk_returns.get(-10.0, 0) or 0, 1),
            })
        scen_df = pd.DataFrame(scen_rows)

        def _hm_red(val):
            """正報酬紅漸層（達標報酬%）— 越高越紅."""
            if pd.isna(val) or val <= 0:
                return ""
            intensity = min(abs(val) / 350.0, 0.55) + 0.06
            color = "color: white;" if intensity > 0.45 else ""
            return f"background-color: rgba(217, 45, 32, {intensity:.2f}); {color}"

        def _hm_green(val):
            """負報酬綠漸層（風險情境）— 越負越綠."""
            if pd.isna(val) or val >= 0:
                return ""
            intensity = min(abs(val) / 100.0, 0.40) + 0.06
            return f"background-color: rgba(7, 148, 85, {intensity:.2f});"

        styler = (
            scen_df.style
            .map(_hm_red, subset=["達標報酬%"])
            .map(_hm_green, subset=["平盤報酬%", "跌5%報酬%", "跌10%報酬%"])
        )
        st.dataframe(
            styler, use_container_width=True, hide_index=True,
            column_config=SCENARIO_COLUMN_CONFIG,
        )

        st.markdown("##### 🥇 達標報酬率前 3 強")
        top3 = scen_results[:3]
        top3_all_identical = len(top3) == 3 and all(
            round(r.risk_returns.get(0.0, 0) or 0, 1)
            == round(r.risk_returns.get(-5.0, 0) or 0, 1)
            == round(r.risk_returns.get(-10.0, 0) or 0, 1)
            for r in top3
        )
        if top3_all_identical:
            st.info(
                "⚠️ Top 3 三檔在所有風險情境下報酬相同：標的在所有下跌情境皆深度價外，"
                "模型目前只反映時間價值衰減（Delta-aware OTM 模型留待後續輪次補強）"
            )

        def _podium_card(rank: int, r) -> str:
            w = r.warrant
            risk_flat = round(r.risk_returns.get(0.0, 0) or 0, 1)
            risk_5 = round(r.risk_returns.get(-5.0, 0) or 0, 1)
            risk_10 = round(r.risk_returns.get(-10.0, 0) or 0, 1)
            be_diff = scenario_target - (r.breakeven or 0)
            eq_d = w.equivalent_delta or 0
            iv = w.iv_mid or 0
            lev = w.leverage or 0
            ratio = w.exercise_ratio or 0
            return f"""
            <div class="podium-card rank-{rank}">
              <div class="podium-ribbon rank-{rank}"></div>
              <div class="podium-head">
                <span class="podium-rank rank-{rank}">{rank}</span>
                <span class="podium-rank-label">達標報酬排序</span>
              </div>
              <div class="podium-ret">{r.expected_return_pct:+.1f}%</div>
              <div class="podium-code">{w.symbol}</div>
              <div class="podium-name">{w.name}</div>
              <div class="podium-kvs">
                <div class="kv"><span class="k">履約 / 天期</span><span class="v">{w.strike:.0f} / {w.days_to_expiry}d</span></div>
                <div class="kv"><span class="k">行使比例</span><span class="v">{ratio:.4f}</span></div>
                <div class="kv"><span class="k">現價 → 預期</span><span class="v">{w.last_price} → {r.expected_warrant_price:.2f}</span></div>
                <div class="kv"><span class="k">損益兩平</span><span class="v">{r.breakeven:.0f} ({be_diff:+.0f})</span></div>
                <div class="kv"><span class="k">等效Δ · IV</span><span class="v">{eq_d:.2f} · {iv:.0f}%</span></div>
                <div class="kv"><span class="k">槓桿</span><span class="v">{lev:.1f}x</span></div>
              </div>
              <div class="podium-warns">
                <div class="w"><span class="label">平盤</span><span class="val">{risk_flat:+.1f}%</span></div>
                <div class="w"><span class="label">跌5%</span><span class="val">{risk_5:+.1f}%</span></div>
                <div class="w"><span class="label">跌10%</span><span class="val">{risk_10:+.1f}%</span></div>
              </div>
            </div>
            """

        podium_cols = st.columns([1.35, 1, 1])
        for i, r in enumerate(top3, 1):
            podium_cols[i - 1].markdown(_podium_card(i, r), unsafe_allow_html=True)

        for i, r in enumerate(top3, 1):
            if r.notes:
                st.caption(f"#{i} {r.warrant.symbol}：" + "　|　".join(r.notes))
elif spot_now is None:
    st.warning("無法反推標的現價（缺履約價/價內外）。")


# --- 候選清單 ---
st.divider()
st.subheader(f"🗂️ 候選清單（通過硬過濾，{len(result.candidates)} 檔）")
if result.candidates:
    df = pd.DataFrame([warrant_to_row(w) for w in result.candidates])
    if "成交量" in df.columns:
        df = df.sort_values("成交量", ascending=False, na_position="last").reset_index(drop=True)
    st.dataframe(df, use_container_width=True, hide_index=True, column_config=PINNED_COLUMNS)
else:
    st.warning("無候選權證")


# --- 個別權證基本資料 ---
if result.candidates:
    st.subheader("🔎 個別權證基本資料")
    options = {f"{w.symbol} {w.name}": w for w in result.candidates}
    pick = st.selectbox("選擇權證", list(options.keys()))
    if pick:
        render_basic_info(options[pick])


# --- 散佈圖 ---
if len(result.candidates) >= 3:
    st.subheader("📊 候選分佈：IV × |等效Δ|")
    df_scat = pd.DataFrame([{
        "symbol": w.symbol, "name": w.name,
        "IV": w.iv_mid,
        "abs_Delta": abs(w.equivalent_delta) if w.equivalent_delta is not None else 0,
        "成交量": w.volume or 0, "槓桿": w.leverage or 0,
    } for w in result.candidates])
    fig = px.scatter(
        df_scat, x="IV", y="abs_Delta", size="成交量", color="槓桿",
        hover_name="name", hover_data=["symbol"],
        labels={"IV": "隱含波動度 %", "abs_Delta": "|等效Δ| (0~1)"},
        title="氣泡=成交量，顏色=槓桿",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 計算邏輯說明 ---
with st.expander("ℹ️ 計算邏輯與 Delta 說明"):
    st.markdown("""
**等效 Delta**

台灣權證 API 回傳的 Delta 是「每單位權證」的 dW/dS，數值很小（如 0.0021）。教科書版本（0~1）需除以行使比例：

```
等效 Delta = 原始 Delta / 行使比例
```

例：原始 Δ=0.0021、行使比例=0.003 → 等效 Δ = **0.700**（深價內）

| 等效 Δ 範圍 | 跟漲能力 | 適合用途 |
|---|---|---|
| 0.1 ~ 0.3 | 慢，深價外 | 高槓桿賭大波動 |
| 0.4 ~ 0.6 | 平衡，ATM | 一般進攻 |
| 0.7 ~ 0.9 | 接近股票 | 低槓桿穩健 |

---

**達標時權證價**（含剩餘時間價值）：
```
expected_W = intrinsic(目標價) + 現有時間價值 × √(剩餘天數 / 現在天期)
```
時間價值用 √t 衰減（Black-Scholes 近似）。

**損益兩平（BE）**：
- 認購：`履約價 + 權證成交價 / 行使比例`
- 認售：`履約價 - 權證成交價 / 行使比例`

**情境過濾條件**：達標時需有正報酬、成交量 ≥ 100、買賣價差比 ≤ 2.5%。
""")
