# Round 3 Implementation Report — 2026-05-07

## Summary

| Item | Status | Notes |
|---|---|---|
| 1. Collapse 3× identical-risk caption into single notice | success | Single `st.info` rendered once above Top-3 cards when all three triplets are identical (rounded to 1 decimal). Per-card caption removed. |
| 2. Surface 標的現價 + 目標價 + 預期漲跌幅 as `st.metric` row | success | `spot_now` reverse-derivation hoisted right after `st.success(...資料來源...)`. New 3-column metric row renders only when `scenario_enabled and spot_now is not None and scenario_target is not None`. Original duplicate caption inside the scenario block removed. |
| 3. Gate bottom synthetic random-walk chart behind Mock source only | success | Whole block wrapped in `if source == "合成樣本 (Mock)":`. `import numpy as np` moved to top-of-file imports. |

**Success: 3 / 3. Failures: 0.**

## Verification

- **pytest**: `32 passed in 0.04s` (run after each item). All tests remain green.
- **`ast.parse`** on `src/streamlit_app.py`: SYNTAX OK (run after each edit).
- **Streamlit restart**: HTTP 200 from `http://localhost:8765/` after restart.
- **Live UI verification (Playwright on http://localhost:8765, 1440×900)**:
  - Symbol = 2330 (default), 認購 (call), 元大權證網, scenario enabled (target 2800, 60 days).
  - Click 開始分析 → wait for `達標報酬率前 3 強`.

## File modified

- `src/streamlit_app.py`: 571 → **585 lines** (+14 net).
  - +1 line: `import numpy as np` at top.
  - +14 lines: hoisted `spot_now` + new 3-column metric row block (right after data-source banner).
  - −2 lines: removed `# --- 反推現價供情境模擬使用 ---` block (10 lines deleted, 0 new where it was).
  - +8 lines: `top3` + `top3_all_identical` + single-notice block above Top-3 loop.
  - −5 lines: removed per-card identical-risk caption + small `st.caption(f"反推標的現價：…")` line inside scenario block.
  - +1 line: `if source == "合成樣本 (Mock)":` wrap; existing block re-indented (no net add) and inline `import numpy as np` removed.

## Screenshots (after)

| File | Verifies |
|---|---|
| `docs/auto-audit/round-3/screenshots-after/01-header-metrics.png` | Top-of-results 3-metric row: 反推標的現價 **2250.1** / 目標價 (60 天後) **2800** / 預期漲跌幅 **+24.4%**. Sits between data-source success banner and 候選清單. |
| `docs/auto-audit/round-3/screenshots-after/02-cards-no-duplicate.png` | Single yellow info notice (`⚠️ Top 3 三檔在所有風險情境下報酬相同：…`) appears ONCE above the three cards. Cards #1 / #2 / #3 carry no per-card duplicate caption underneath. |
| `docs/auto-audit/round-3/screenshots-after/03-bottom-no-mock-chart.png` | Page bottom in yuanta mode ends at the Delta-explanation expander — no synthetic random-walk chart present. Confirmed via `document.body.innerText.includes('標的股價 vs Top 推薦權證價') === false`. |
| `docs/auto-audit/round-3/screenshots-after/04-scenario-table.png` | Scenario table sanity check — 73 檔 still passes filtering, table renders with all expected columns (達標權證價 / 達標報酬% / etc.) and Top-3 cards section visible underneath. |

## Observations from after-screenshots

- 反推現價 came out at 2250.1 vs Round 2 review's "real spot 2250" reference; matches expectations.
- Top-3 risk numbers remain identical (#1 −21.7% × 3, #2 −21.1% × 3, #3 −29.0% × 3) — this is expected because the Delta-aware OTM model gap was deliberately deferred (Skipped #1 in review). The single info notice now correctly explains the cause without repeating itself.
- 預期漲跌幅 +24.4% is a useful at-a-glance signal — user can immediately judge whether the target is realistic without scrolling past the candidate table.
- Bottom-chart removal makes the yuanta page substantially shorter and removes the misleading "1100-base spot path vs real 2250" artifact noted in the review.
- 候選清單 still correctly sorted by 成交量 desc (3604 → 3169 → 3061 …) confirming R1/R2 changes intact.
- pytest still 32/32 in 0.04s — no regression.

## Anomalies

None blocking. One minor note: full-page Playwright screenshot for `03-bottom-no-mock-chart.png` rendered at viewport size because Streamlit uses internal scrollable containers that don't extend `document.body.scrollHeight`; absence of the synthetic chart was confirmed independently via JS string-search of `document.body.innerText`.

## Not committed

Per task spec, no `git commit` / `git push` performed. Parent agent will commit/push.
