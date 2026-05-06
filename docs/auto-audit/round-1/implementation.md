# Round 1 — Implementation Report

## Summary

| Item | Status |
|---|---|
| **A** — Use 等效Δ in candidate table & bubble chart | ✅ Success |
| **B** — Tooltips on scenario columns + identical-risk caption | ✅ Success |

Success: 2 / Failure: 0 / Blockers: none.

## Item A — 等效Δ in candidate table & bubble chart

**File modified:** `src/streamlit_app.py`

Changes:
1. `warrant_to_row(w)` (~ line 150) — replaced `"Delta": w.delta` with
   `"等效Δ": round(w.equivalent_delta, 3) if w.equivalent_delta is not None else None`.
2. Bubble chart block (~ line 336) — replaced `abs(w.delta) if w.delta else 0`
   with `abs(w.equivalent_delta) if w.equivalent_delta is not None else 0`,
   updated y-axis label to `"|等效Δ| (0~1)"`, subheader to
   `"📊 候選分佈：IV × |等效Δ|"`, and chart title to mention 等效Δ.

Verification:
- Candidate table 03-candidates.png shows `等效Δ` column with values 0.425, 0.5, 0.525, etc.
- Subheader confirmed: `📊 候選分佈：IV × |等效Δ|`.

## Item B — Scenario tooltips + identical-risk caption

**File modified:** `src/streamlit_app.py`

Changes:
1. Added `SCENARIO_COLUMN_CONFIG` dict (extends `PINNED_COLUMNS`) with
   `st.column_config.NumberColumn(..., help="...")` entries for 等效Δ, IV%,
   槓桿, 履約價, 價內外%, 天期, 損益兩平, 達標權證價, 達標報酬%, 平盤報酬%,
   跌5%報酬%, 跌10%報酬%. Pinned columns 權證代碼/權證名稱inherit pinned=True.
2. Updated the scenario `st.dataframe(...)` call to use `column_config=SCENARIO_COLUMN_CONFIG`.
3. In the per-card "🥇 達標報酬率前 3 強" loop, computed
   `risk_flat / risk_5 / risk_10` (rounded to 1 decimal) and rendered
   `st.caption("⚠️ 三檔風險情境報酬相同：標的在所有下跌情境皆深度價外，模型目前只反映時間價值衰減（Delta-aware OTM 模型留待後續輪次補強）")`
   when all three are equal.

Verification (see 04b-scenario-cards.png):
- Top 3 cards all show `-21.7%`, `-21.1%`, `-29.0%` triplets and the new caption appears under each.

## Test & syntax results

- `python -c "import ast; ast.parse(open('src/streamlit_app.py').read())"` — OK after both items.
- `python -m pytest tests/ -q` — **32 passed in 0.04s** (after each item).

## Streamlit restart

- Killed prior process: `pkill -f 'streamlit run.*streamlit_app'`
- Restarted on port 8765 (headless).
- `curl http://localhost:8765/` → **HTTP 200**.

## File line count

`src/streamlit_app.py`: 569 lines (was 508; +61 due to SCENARIO_COLUMN_CONFIG and risk-equality caption).

## Screenshots (after)

- `docs/auto-audit/round-1/screenshots-after/01-landing.png`
- `docs/auto-audit/round-1/screenshots-after/02-results-top.png`
- `docs/auto-audit/round-1/screenshots-after/03-candidates.png` (shows 等效Δ column)
- `docs/auto-audit/round-1/screenshots-after/04-scenario.png` (scenario table with tooltipped headers)
- `docs/auto-audit/round-1/screenshots-after/04b-scenario-cards.png` (cards with new "三檔風險情境報酬相同" caption)
