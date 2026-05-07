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

/* Compact meta row (取代大 alert) */
.meta-row {
  font-size: 12.5px;
  color: var(--ink-3);
  padding: 8px 12px;
  background: var(--surface-2);
  border: 1px solid var(--line-1);
  border-radius: var(--r-md);
  margin: 12px 0 8px;
}
.meta-row strong {
  color: var(--ink-1);
  font-weight: 500;
  font-family: 'Geist Mono', monospace;
}

/* Tighten Streamlit's default vertical spacing */
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
  margin-bottom: 0 !important;
}
[data-testid="stVerticalBlock"] {
  gap: 0.5rem !important;
}
hr { margin: 16px 0 !important; }
[data-testid="stMarkdownContainer"] hr { margin: 8px 0 !important; }

/* Subtle alerts (info/success/warning are smaller) */
[data-testid="stAlertContainer"] {
  padding: 8px 12px !important;
  font-size: 12.5px !important;
}

/* ====== Input card layout（取自 React 設計） ====== */
.input-card-shell {
  background: var(--surface);
  border: 1px solid var(--line-1);
  border-radius: var(--r-lg);
  padding: 18px 20px 14px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
  margin-bottom: 16px;
}
.input-card-shell + [data-testid="stHorizontalBlock"] {
  margin-top: -10px !important;
}
.input-meta-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12.5px;
  color: var(--ink-3);
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line-1);
}
.input-meta-strip .meta-left { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
.input-meta-strip .meta-left .sep { color: var(--line-3); }
.input-meta-strip .meta-left .up-color { color: var(--up); font-weight: 500; }
.input-meta-strip .meta-left .down-color { color: var(--down); font-weight: 500; }

/* Make inputs inside input card look unified with design */
.input-card-shell + [data-testid="stHorizontalBlock"] [data-testid="stWidgetLabel"] p {
  margin-bottom: 4px !important;
}

/* Direction radio styled as segmented control */
[data-testid="stRadio"] [role="radiogroup"] {
  gap: 4px !important;
  background: var(--surface-2);
  border: 1px solid var(--line-2);
  border-radius: var(--r-md);
  padding: 3px;
  display: inline-grid !important;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  width: 100%;
}
[data-testid="stRadio"] [role="radiogroup"] label {
  margin: 0 !important;
  padding: 6px 10px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-2);
  transition: all .12s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
  background: var(--surface);
  color: var(--ink-1);
  box-shadow: var(--shadow-xs), 0 0 0 0.5px var(--line-2);
}
[data-testid="stRadio"] [role="radiogroup"] input { display: none !important; }

/* Page head dynamic title */
.page-head h1 .stock-name {
  color: var(--ink-3);
  font-weight: 500;
  margin-left: 4px;
}

/* ====== 合理價計算機 ====== */
.calc-section-head { margin-top: 8px; margin-bottom: 12px; }
.calc-section-head h2 { font-size: 20px; font-weight: 600; margin: 0 0 4px; letter-spacing: -0.01em; }
.calc-section-head .sub { color: var(--ink-3); font-size: 13px; margin: 0; }

.calc-card {
  background: var(--surface);
  border: 1px solid var(--line-1);
  border-radius: var(--r-lg);
  padding: 18px 20px 16px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
  margin-bottom: 24px;
}
.calc-divider {
  border-top: 1px solid var(--line-1);
  margin: 16px 0;
}

/* BS 合理價 大字深藍卡 */
.bs-fair-card {
  background: linear-gradient(160deg, #1d2540 0%, #2a3658 100%) !important;
  border-radius: var(--r-md) !important;
  padding: 16px 20px !important;
  height: 100%;
}
.bs-fair-card .label {
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  color: rgba(255,255,255,0.7) !important;
  margin-bottom: 6px !important;
}
.bs-fair-card .value {
  font-family: 'Geist Mono', monospace !important;
  font-feature-settings: 'tnum' !important;
  font-size: 34px !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em !important;
  line-height: 1 !important;
  color: #ffffff !important;
}
.bs-fair-card .meta {
  font-size: 11px !important;
  color: rgba(255,255,255,0.55) !important;
  margin-top: 10px !important;
  font-family: 'Geist Mono', monospace !important;
}

.tick-card {
  background: var(--surface);
  border: 1px solid var(--line-2);
  border-radius: var(--r-md);
  padding: 14px 18px;
  height: 100%;
}
.tick-card .label {
  font-size: 11.5px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: var(--ink-3);
  margin-bottom: 6px;
  display: flex; align-items: center; gap: 4px;
}
.tick-card .value {
  font-family: 'Geist Mono', monospace;
  font-feature-settings: 'tnum';
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1;
}
.tick-card.buy { border-color: var(--down-line); }
.tick-card.buy .value { color: var(--down); }
.tick-card.sell { border-color: var(--up-line); }
.tick-card.sell .value { color: var(--up); }
.tick-card .meta { font-size: 11px; color: var(--ink-3); margin-top: 6px; }

/* 計算機 meta line */
.calc-meta-line {
  font-size: 12.5px;
  color: var(--ink-3);
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.calc-meta-line .sep { color: var(--line-3); }
.calc-meta-line strong {
  color: var(--ink-1);
  font-weight: 500;
  font-family: 'Geist Mono', monospace;
}
.calc-meta-line .dev-up { color: var(--up); font-weight: 500; }
.calc-meta-line .dev-down { color: var(--down); font-weight: 500; }

/* 敏感度表 */
.sens-section-title {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink-2);
  margin: 14px 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.sens-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'Geist Mono', monospace;
  font-size: 12.5px;
  font-feature-settings: 'tnum';
}
.sens-table th {
  text-align: right;
  padding: 6px 10px;
  border-bottom: 1px solid var(--line-1);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-3);
  font-family: 'Geist', sans-serif;
}
.sens-table th:first-child { text-align: left; }
.sens-table td {
  padding: 7px 10px;
  text-align: right;
  border-bottom: 1px solid var(--line-1);
  color: var(--ink-1);
}
.sens-table td:first-child { text-align: left; color: var(--ink-3); }
.sens-table tr.current { background: var(--surface-2); font-weight: 600; }
.sens-table tr.current td { color: var(--ink-1); }
.sens-table .px-up { color: var(--up); }
.sens-table .px-down { color: var(--down); }
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

# --- Page head（用 placeholder 讓分析後 H1 能即時更新標的名稱）---
_h1_placeholder = st.empty()


def _render_h1(sym: str = "", name: str = "") -> None:
    if sym:
        title = f"情境分析 — {sym}"
        if name:
            title += f' <span class="stock-name">{name}</span>'
    else:
        title = "情境分析 — 找尋能在目標日獲利的權證"
    _h1_placeholder.markdown(
        f"""
        <div class="page-head">
          <h1>{title}</h1>
          <p class="page-sub">輸入標的、目標價與日期，工具回傳「在這個情境下哪些權證能獲利」的排序，並提供 Black-Scholes 合理價計算機輔助下單。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# 先用 session_state 已經有的值畫一次（之後分析跑完會被覆寫）
_render_h1(
    st.session_state.get("analyzed_symbol", ""),
    st.session_state.get("analyzed_underlying_name", ""),
)


# --- 主畫面輸入區（單列含 CTA，仿 React 設計）---
st.markdown('<div class="input-card-shell"></div>', unsafe_allow_html=True)
input_cols = st.columns([1.1, 1.0, 0.85, 1.05, 1.15, 1.0])
with input_cols[0]:
    symbol = st.text_input("標的代碼", value="2330", help="例：2330（台積電）、2454（聯發科）")
with input_cols[1]:
    direction_label = st.radio(
        "方向",
        ["認購", "認售"],
        horizontal=True,
        label_visibility="visible",
    )
    direction = "call" if direction_label == "認購" else "put"
with input_cols[2]:
    top_n = st.slider("TOP N", 3, 10, 5)
with input_cols[3]:
    scenario_target = st.number_input(
        "目標標的價",
        min_value=1.0, value=2800.0, step=10.0,
        help="您預期標的會到達的價格（NT$）",
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
with input_cols[5]:
    # 對齊 input 高度：先放空 label 再放 button
    st.markdown('<div style="height:26px"></div>', unsafe_allow_html=True)
    run = st.button("🔍 開始分析", type="primary", use_container_width=True)

# 下方 meta strip（紅漲綠跌、距今天數、資料來源）
st.markdown(
    f"""
    <div class="input-meta-strip">
      <div class="meta-left">
        <span>距今 <strong style="color:var(--ink-1);font-family:'Geist Mono',monospace">{scenario_days}</strong> 日</span>
        <span class="sep">|</span>
        <span>資料來源：元大權證網</span>
        <span class="sep">|</span>
        <span>台股慣例：<span class="up-color">紅漲</span> / <span class="down-color">綠跌</span></span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- helpers ---
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


# 統一表格小數位數的 format spec（同時餵 styler.format 和 column_config）
_TABLE_FORMAT = {
    "成交價": "{:.2f}",
    "等效Δ": "{:.3f}",
    "IV%": "{:.1f}",
    "槓桿": "{:.2f}",
    "差槓比": "{:.3f}",
    "履約價": "{:.2f}",
    "行使比例": "{:.4f}",
    "價內外%": "{:.1f}",
    "天期": "{:.0f}",
    "買賣價差比%": "{:.2f}",
    "成交量(張)": "{:,.0f}",
    "損益兩平": "{:,.0f}",
    "達標權證價": "{:.2f}",
    "達標報酬%": "{:+.1f}",
    "平盤報酬%": "{:+.1f}",
    "跌5%報酬%": "{:+.1f}",
    "跌10%報酬%": "{:+.1f}",
}


def _r(v, n):
    """安全 round；None / NaN 回傳 None."""
    if v is None:
        return None
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def _scen_row(r) -> dict:
    """情境表/候選表共用的 row builder（在這裡就把小數位數定下來）."""
    w = r.warrant
    return {
        "權證代碼": w.symbol,
        "權證名稱": w.name,
        "認購售": "認購" if w.direction == "call" else "認售",
        "成交價": _r(w.last_price, 2),
        "等效Δ": _r(w.equivalent_delta, 3),
        "IV%": _r(w.iv_mid, 1),
        "槓桿": _r(w.leverage, 2),
        "差槓比": _r(w.spread_to_leverage, 3),
        "履約價": _r(w.strike, 2),
        "行使比例": _r(w.exercise_ratio, 4),
        "價內外%": _r(w.moneyness_pct, 1),
        "天期": w.days_to_expiry,
        "買賣價差比%": _r(w.bid_ask_spread_pct, 2),
        "成交量(張)": w.volume,
        "損益兩平": _r(r.breakeven, 0),
        "達標權證價": _r(r.expected_warrant_price, 2),
        "達標報酬%": _r(r.expected_return_pct, 1),
        "平盤報酬%": _r(r.risk_returns.get(0.0), 1),
        "跌5%報酬%": _r(r.risk_returns.get(-5.0), 1),
        "跌10%報酬%": _r(r.risk_returns.get(-10.0), 1),
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
        "差槓比": f"{w.spread_to_leverage:.3f}" if w.spread_to_leverage is not None else "-",
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
    st.session_state["analyzed_symbol"] = symbol
    underlying_name_now = ""
    if result.candidates:
        underlying_name_now = result.candidates[0].underlying_name or ""
        st.session_state["analyzed_underlying_name"] = underlying_name_now
    # 分析完成立即更新 H1（不必等下次 rerun）
    _render_h1(symbol, underlying_name_now)


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

    # ── 切換權證 / 模式時，重設下面 widgets 的 session_state ──
    # 否則 slider/input 會卡在前一檔的 IV 或 spot
    spot_tick_calc = tick_size(default_spot)
    fingerprint = (mode, sel_w.symbol, sel_w.strike, round(default_iv, 2), round(default_spot, 2))
    if st.session_state.get("calc_fingerprint") != fingerprint:
        st.session_state["calc_spot"] = float(round_to_tick(default_spot, "nearest"))
        st.session_state["calc_iv"] = float(default_iv)
        st.session_state["calc_step"] = float(spot_tick_calc)
        st.session_state["calc_fingerprint"] = fingerprint

    # ── 兩欄分隔：左邊輸入、右邊輸出 ──
    spot_tick = tick_size(default_spot)
    left_col, right_col = st.columns([1.05, 1])

    with left_col:
        cc = st.columns(2)
        with cc[0]:
            spot = st.number_input(
                "現在標的價", min_value=0.01,
                value=float(round_to_tick(default_spot, "nearest")),
                step=float(spot_tick),
                help=f"標的 tick={spot_tick}",
                key="calc_spot",
            )
        with cc[1]:
            spot_step = st.number_input(
                "敏感度步長（元）",
                min_value=float(spot_tick), value=float(spot_tick),
                step=float(spot_tick), key="calc_step",
            )
        iv_pct = st.slider(
            f"IV %（{default_iv:.1f} 為市場值）", 5.0, 200.0,
            float(default_iv), step=0.5, key="calc_iv",
        )
        cc2 = st.columns(2)
        with cc2[0]:
            r_pct = st.slider(
                "無風險利率 %", 0.0, 10.0, 2.0, step=0.25, key="calc_r",
            )
        with cc2[1]:
            q_pct = st.slider(
                "股息率 %", 0.0, 10.0, 0.0, step=0.25, key="calc_q",
                help="台積電約 1.8%",
            )

    res = fair_warrant_price(
        sel_w, spot=spot, iv_pct=iv_pct,
        r=r_pct / 100.0, q=q_pct / 100.0,
    )

    with right_col:
        if res is None:
            st.warning("缺資料（履約價/IV/天數）無法計算")
            return

        tick_down, tick_up = adjacent_ticks(res.fair_price)
        fair_aligned = round_to_tick(res.fair_price, "nearest")
        ftick = tick_size(res.fair_price)

        # 三張輸出卡（深藍 BS + 買進綠 + 賣出紅）
        out_cols = st.columns([1.4, 1, 1])
        out_cols[0].markdown(
            f"""<div class="bs-fair-card">
              <div class="label">BS 合理價（已對齊 TICK）</div>
              <div class="value">{fair_aligned:.2f}</div>
              <div class="meta">tick = {ftick} · 模型：BS-Merton</div>
            </div>""",
            unsafe_allow_html=True,
        )
        out_cols[1].markdown(
            f"""<div class="tick-card buy">
              <div class="label">📥 買進可掛</div>
              <div class="value">{tick_down:.2f}</div>
              <div class="meta">合理價 −1 tick</div>
            </div>""",
            unsafe_allow_html=True,
        )
        out_cols[2].markdown(
            f"""<div class="tick-card sell">
              <div class="label">📤 賣出可掛</div>
              <div class="value">{tick_up:.2f}</div>
              <div class="meta">合理價 +1 tick</div>
            </div>""",
            unsafe_allow_html=True,
        )

        # Meta line（市價 / 偏差 / 內含值 / 時間價值 / 到期）
        meta_parts = []
        if res.market_price and res.deviation_pct is not None:
            cls = "dev-up" if res.deviation_pct >= 0 else "dev-down"
            dot = "🔴" if res.deviation_pct < 0 else "🟢"
            meta_parts.append(
                f'市價 <strong>{res.market_price}</strong>'
                f'<span class="sep">·</span>'
                f'偏差 {dot} <span class="{cls}">{res.deviation_pct:+.2f}%</span>'
            )
        meta_parts.append(
            f'內含值 <strong>{res.intrinsic:.3f}</strong> + 時間價值 <strong>{res.time_value:.3f}</strong>'
        )
        meta_parts.append(f'到期 <strong>{res.days_to_expiry}</strong> 天')
        st.markdown(
            '<div class="calc-meta-line">'
            + '<span class="sep">·</span>'.join(meta_parts)
            + '</div>',
            unsafe_allow_html=True,
        )

        # 敏感度表（自繪 HTML 表）
        steps_signed = [
            (-3, -3 * spot_step), (-2, -2 * spot_step), (-1, -1 * spot_step),
            (0, 0.0),
            (1, 1 * spot_step), (2, 2 * spot_step), (3, 3 * spot_step),
        ]
        sens = sensitivity_table(
            sel_w, spot, [ds for _, ds in steps_signed],
            iv_pct=iv_pct, r=r_pct / 100.0, q=q_pct / 100.0,
        )
        rows_html = []
        rows_html.append(
            f'<div class="sens-section-title">敏感度表 · 步長 ±{spot_step:g}</div>'
            f'<table class="sens-table">'
            f'<thead><tr>'
            f'<th>股價變動</th><th>標的價</th><th>合理價</th><th>買進掛</th><th>賣出掛</th>'
            f'</tr></thead><tbody>'
        )
        for (mult, ds), (s, p) in zip(steps_signed, sens):
            row_cls = "current" if mult == 0 else ""
            label = f"{mult:+d}× = {ds:+.0f}" if mult != 0 else "0（現價）"
            if p is None:
                rows_html.append(
                    f'<tr class="{row_cls}"><td>{label}</td>'
                    f'<td>{s:.0f}</td><td>–</td><td>–</td><td>–</td></tr>'
                )
            else:
                bd, bu = adjacent_ticks(p)
                fair_str = f"{round_to_tick(p, 'nearest'):.2f}"
                px_cls = "px-up" if mult > 0 else ("px-down" if mult < 0 else "")
                rows_html.append(
                    f'<tr class="{row_cls}"><td>{label}</td>'
                    f'<td>{round_to_tick(s, "nearest"):.0f}</td>'
                    f'<td class="{px_cls}">{fair_str}</td>'
                    f'<td>{bd:.2f}</td><td>{bu:.2f}</td></tr>'
                )
        rows_html.append('</tbody></table>')
        st.markdown("".join(rows_html), unsafe_allow_html=True)


# 合理價計算機 — 移出 expander，永遠可見
st.markdown(
    """
    <div class="calc-section-head">
      <h2>合理價計算機</h2>
      <p class="sub">Black-Scholes 推算合理價並對齊 tick；7 列敏感度表覆蓋 ±3× 步長。</p>
    </div>
    """,
    unsafe_allow_html=True,
)
with st.container():
    _render_calculator(list(result.candidates) if result else [])


# --- 沒按分析就停在這 ---
if not has_run or result is None:
    st.info("👆 想看完整分析？輸入標的、方向、目標價/日期 → 點上方「🔍 開始分析」")
    st.stop()


_notes_inline = ""
if result.notes:
    _notes_inline = "　|　" + "、".join(result.notes)


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

    # 小字 meta 行：資料來源 + filter notes（取代原本三個大綠/藍 alert）
    st.markdown(
        f'<div class="meta-row">資料來源 <strong>{result.fetch_source}</strong>　|　'
        f'原始候選 <strong>{result.raw_count:,}</strong> 檔　|　'
        f'硬過濾後 <strong>{len(result.candidates)}</strong> 檔'
        f'{_notes_inline}</div>',
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
    "認購售": st.column_config.TextColumn("認購售"),
    "成交價": st.column_config.NumberColumn("成交價", format="%.2f"),
    "等效Δ": st.column_config.NumberColumn("等效Δ", format="%.3f", help="教科書 0~1 Delta（已除以行使比例）；認購正、認售負"),
    "IV%": st.column_config.NumberColumn("IV%", format="%.1f", help="隱含波動度（買價/賣價隱波取中位）"),
    "槓桿": st.column_config.NumberColumn("槓桿", format="%.2f", help="實質槓桿（FLD_LEVERAGE）"),
    "差槓比": st.column_config.NumberColumn("差槓比", format="%.3f", help="買賣價差比% / 實質槓桿（越低越好；用 1x 槓桿換來的價差成本）"),
    "履約價": st.column_config.NumberColumn("履約價", format="%.2f", help="權證的履約價"),
    "行使比例": st.column_config.NumberColumn("行使比例", format="%.4f"),
    "價內外%": st.column_config.NumberColumn("價內外%", format="%.1f", help="目前價內(+) 或價外(-) 的百分比"),
    "天期": st.column_config.NumberColumn("天期", format="%d", help="權證剩餘日曆天數"),
    "買賣價差比%": st.column_config.NumberColumn("買賣價差比%", format="%.2f", help="(賣價-買價)/中價 ×100%，FLD_BUY_SELL_RATE"),
    "成交量(張)": st.column_config.NumberColumn("成交量(張)", format="%d"),
    "損益兩平": st.column_config.NumberColumn("損益兩平", format="%.0f", help="標的需漲(call)/跌(put)到此價才回本"),
    "達標權證價": st.column_config.NumberColumn("達標權證價", format="%.2f", help="若達目標日標的到目標價，預期權證的價格"),
    "達標報酬%": st.column_config.NumberColumn("達標報酬%", format="%+.1f", help="達標時相對現價的報酬"),
    "平盤報酬%": st.column_config.NumberColumn("平盤報酬%", format="%+.1f", help="若標的不動到目標日，預期權證價變化"),
    "跌5%報酬%": st.column_config.NumberColumn("跌5%報酬%", format="%+.1f", help="若標的下跌 5% 到目標日的報酬"),
    "跌10%報酬%": st.column_config.NumberColumn("跌10%報酬%", format="%+.1f", help="若標的下跌 10% 到目標日的報酬"),
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
        SORT_KEYS = {
            "達標報酬% (高→低)": (lambda r: r.expected_return_pct or -1e9, True),
            "等效Δ |絕對值| (高→低)": (lambda r: abs(r.warrant.equivalent_delta or 0), True),
            "差槓比 (低→高)": (lambda r: r.warrant.spread_to_leverage or 1e9, False),
            "履約價 (低→高)": (lambda r: r.warrant.strike or 1e9, False),
            "履約價 (高→低)": (lambda r: r.warrant.strike or 0, True),
            "天期 (短→長)": (lambda r: r.warrant.days_to_expiry or 1e9, False),
            "天期 (長→短)": (lambda r: r.warrant.days_to_expiry or 0, True),
            "成交量 (高→低)": (lambda r: r.warrant.volume or 0, True),
            "IV% (低→高)": (lambda r: r.warrant.iv_mid or 1e9, False),
            "槓桿 (高→低)": (lambda r: r.warrant.leverage or 0, True),
        }
        sort_choice = st.selectbox(
            "排序方式",
            list(SORT_KEYS.keys()),
            index=0, key="scen_sort",
            help="也可以直接點表格欄位 header 排序",
        )
        key_fn, reverse = SORT_KEYS[sort_choice]
        scen_sorted = sorted(scen_results, key=key_fn, reverse=reverse)
        st.success(f"✅ 通過情境過濾：{len(scen_results)} 檔　|　依「{sort_choice}」排序")

        scen_df = pd.DataFrame([_scen_row(r) for r in scen_sorted[:20]])
        styler = (
            scen_df.style
            .format(_TABLE_FORMAT, na_rep="–")
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


# --- 候選清單（同情境表欄位，但不做情境過濾）---
st.divider()
st.subheader(f"🗂️ 候選清單（通過硬過濾，{len(result.candidates)} 檔）")
if result.candidates and spot_now is not None:
    # 對所有 candidates 跑情境模擬（不過濾），讓表格欄位與情境表完全相同
    cand_inputs = ScenarioInputs(
        target_price=float(scenario_target),
        days_to_target=int(scenario_days),
        spot_now=spot_now,
        risk_drops_pct=(0.0, -5.0, -10.0),
    )
    cand_batch = evaluate_scenarios(
        result.candidates, cand_inputs,
        require_alive_at_target=False,
        require_profit_at_target=False,
        min_volume=0, max_spread_pct=999.0,
    )
    cand_df = pd.DataFrame([_scen_row(r) for r in cand_batch.results])
    if "成交量(張)" in cand_df.columns:
        cand_df = cand_df.sort_values("成交量(張)", ascending=False, na_position="last").reset_index(drop=True)
    cand_styler = (
        cand_df.style
        .format(_TABLE_FORMAT, na_rep="–")
        .map(_hm_red, subset=["達標報酬%"])
        .map(_hm_green, subset=["平盤報酬%", "跌5%報酬%", "跌10%報酬%"])
    )
    st.dataframe(
        cand_styler, use_container_width=True, hide_index=True,
        column_config=SCENARIO_COLUMN_CONFIG,
    )
elif not result.candidates:
    st.warning("無候選權證")
else:
    st.warning("無法反推現價，候選清單無法評估情境")


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
