# Round 4 Implementation Report

Date: 2026-05-07
Branch: main
Streamlit: http://localhost:8765

## Summary

| Item | Status |
|------|--------|
| 1 — Replace English profile slugs with 中文 in overrides expander | success |
| 2 — Warn when scenario target direction conflicts with call/put | success |
| 3 — Add `st.divider()` between sidebar groups | success |

Success: 3 / 3
Failures: 0
Blockers: none

## File diffs (logical summary)

All edits in `src/streamlit_app.py`:

### Item 1
- Added `PROFILE_LABELS_ZH: dict[Profile, str] = {"stable": "穩健型", "aggressive": "進攻型"}` next to the `profiles` tuple definition.
- In the override loop, replaced `f"**{p}**"` with `f"**{PROFILE_LABELS_ZH[p]}**"`.
- Replaced the four slider labels:
  - `f"[{p}] 剩餘天數 ≥"` → `f"[{PROFILE_LABELS_ZH[p]}] 剩餘天數 ≥"`
  - `f"[{p}] 成交量 ≥"` → `f"[{PROFILE_LABELS_ZH[p]}] 成交量 ≥"`
  - `f"[{p}] 買賣價差比 ≤"` → `f"[{PROFILE_LABELS_ZH[p]}] 買賣價差比 ≤"`
  - `f"[{p}] IV ≤"` → `f"[{PROFILE_LABELS_ZH[p]}] IV ≤"`
- Widget keys (`key=f"d_{p}"`, `v_{p}`, `s_{p}`, `i_{p}`) kept unchanged → Streamlit widget identity preserved across re-runs.

### Item 2
- Inside the `if scenario_enabled and spot_now is not None and scenario_target is not None:` block, immediately after the `mc3.metric(...)` call, added two-branch `st.warning(...)` for direction mismatch:
  - `direction == "call" and pct < 0` → "認購權證在標的下跌時通常虧損 — 您是否想改選「認售 (put)」？"
  - `direction == "put" and pct > 0` → "認售權證在標的上漲時通常虧損 — 您是否想改選「認購 (call)」？"

### Item 3
- Replaced `st.sidebar.markdown("---")` (above 情境 section) with `st.sidebar.divider()`.
- Added new `st.sidebar.divider()` immediately above `with st.sidebar.expander("進階：硬過濾閾值（覆寫預設）"):`.
- Net effect: 4 visually separated sidebar groups (標的/方向/資料源/Top N → 情境 → 進階閾值 → 開始分析).

## Verification

- `python -c "import ast; ast.parse(open('src/streamlit_app.py').read())"` → succeeded after every item.
- `python -m pytest tests/ -q` → 32 passed (run after each item).
- Streamlit restart → HTTP 200 on http://localhost:8765/.

## Screenshots

Saved under `docs/auto-audit/round-4/screenshots-after/`:

1. `01-overrides-zh.png` — Overrides expander opened, "啟用自訂閾值" checked. Header reads "穩健型" and slider reads "[穩健型] 剩餘天數 ≥ 30" (Chinese labels confirmed).
2. `02-sidebar-dividers.png` — Sidebar collapsed/idle: 4 groups separated by 3 horizontal dividers (after Top N, before 情境 checkbox, before 進階 expander). Dividers are slightly more prominent than the previous markdown `---` (Streamlit's native divider styling).
3. `03-direction-warning-call.png` — 認購 + 目標標的價=2000 + 60d. Top metric row shows 反推現價 2250.1 / 目標價 2000 / 預期漲跌幅 -11.1%. Yellow warning displays directly below: "⚠️ 目標價 2000 低於反推現價 2250.1（-11.1%）。認購權證在標的下跌時通常虧損 — 您是否想改選「認售 (put)」？".
4. `04-no-warning.png` — 認購 + 目標標的價=2800 + 60d. Top metric row shows 反推現價 2250.1 / 目標價 2800 / 預期漲跌幅 +24.4%. No warning area between metrics and "候選清單" heading (correct: pct > 0 with call → no mismatch).

## Anomalies / observations

- The "認售 / put + pct > 0" branch was not directly screenshotted (per instructions, only call+target=2000 and call+target=2800). The code path is symmetric to the call branch and uses the same `st.warning` shape.
- During scenario re-run the sidebar shows 進階閾值 expander collapsed (state reset on rerun) — expected behavior of `st.expander` without explicit `expanded=` flag.
- The two `[stable]` / `[aggressive]` info messages above the metric row (`12 檔因缺 Greeks/IV 被排除`) still use English profile slugs. They originate from backend `result.notes` (not part of the override expander UI). The review.md scope only covered the overrides expander; backend notes are out of scope for Round 4 Item 1 and remain unchanged.
- pytest count constant at 32/32 across all three edits.

## Files modified

- `src/streamlit_app.py` — all three items consolidated into one file.

(No other files touched. Tests unchanged. No new dependencies.)
