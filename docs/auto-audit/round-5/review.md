# Round 5 Review (FINAL) — 2026-05-07 05:45 (Asia/Taipei)

## Observations

- All R1–R4 changes are landed and rendering correctly (`screenshots/02-results.png`):
  - Header metric strip 反推標的現價 / 目標價 / 預期漲跌幅 sits cleanly above the candidate table.
  - Candidate table is sorted by 成交量 desc (4851 → 3604 → 3169 → 3061 …, 223 檔 通過硬過濾).
  - Bubble chart `IV × |等效Δ|` renders in the middle (`screenshots/03-candidates.png`).
  - Scenario simulation table + Top-3 cards render with single 「Top 3 三檔在所有風險情境下報酬相同」 info notice (`screenshots/04-scenario.png` / `05-cards.png`).
  - Direction warning fires correctly: `認購 + target=1800 < 反推現價 2250.1 (-20.0%)` triggers yellow warning「⚠️ 目標價 1800 低於反推現價 2250.1（-20.0%）。認購權證在標的下跌時通常虧損 — 您是否想改選「認售 (put)」？」(`screenshots/06-direction-warning.png`).
  - TWSE source still works as fallback with 中文 lite-mode notice (`screenshots/07-twse.png`).
  - Sidebar: 4 visually distinct sections separated by dividers.
- 32/32 tests still pass.
- **Inconsistency — backend `result.notes` still emits English profile slugs** (`screenshots/02-results.png`, `06-direction-warning.png`): two info banners read literally `[stable] 12 檔因缺 Greeks/IV 被排除` and `[aggressive] 12 檔因缺 Greeks/IV 被排除` directly above the header metric strip. The override-expander headers, sidebar reference table, and every other UI surface uses 中文 (穩健型 / 進攻型 / 低隱波穩健型 / 高槓桿進攻型). These two banners are now the only English-slug leak that an end user sees on every successful run with Yuanta data. R4 review explicitly flagged this as out-of-scope (touched a different file) — it is the cleanest one-line wrap-up consistency fix for Round 5. Source: `src/twse_warrant/analyzers/rank.py:209-286`, four `result.notes.append(f"[{profile}] …")` call sites.
- **README is 4 rounds out of date**: `README.md` last touched at R0. It has no mention of:
  - 等效Δ (R1) — the entire equivalent-delta concept that now drives the candidate table column and the bubble chart axis.
  - 情境模擬 (R0/R1) — target-price + days input → expected return + risk-scenario table; this is now the second main UX path next to the recommendation table.
  - 反推現價 metric (R3) — header metric strip.
  - 中文 profile labels (R4) — README still uses 「低隱波穩健型」/「高槓桿進攻型」 in the recommendation-style table but never connects them to the sidebar/expander 「穩健型」/「進攻型」 short forms.
  - 方向衝突警示 (R4).
  - Default sort by 成交量 (R2).
  - The README says "20 個單元測試" but the suite has been at 32 for several rounds (`pytest tests/ -q` confirms `32 passed in 0.04s`).
  - The README "Streamlit UI" section says "輸入標的 → 選方向 → 選風格 → 看推薦 + 候選表 + IV-Delta 散點圖" — the 風格 step no longer maps to a visible "推薦" output (per R0/R1 notes, the `result.recommendations[profile]` tables aren't rendered on the main page anymore; only the candidate union + scenario table + Top-3 cards are shown). The README user journey is misleading now.
- `import numpy as np` (line 4) and `import plotly.graph_objects as go` (line 7) are still needed — they're used inside the Mock-only synthetic-chart block (line 588-594). Not dead. No cleanup possible without dropping the Mock chart entirely (out of scope; serves a UX purpose for the demo path).
- `src/twse_warrant/__init__.py` public exports are clean (`analyze`, `AnalysisResult`, `Direction`, `Profile`, `ScoredWarrant`, `Warrant`) — `__all__` matches imports, no stale entries. No action needed.
- No `# TODO` / `# FIXME` markers anywhere in `src/` or `tests/`.
- Open items still on the backlog (per R1-R4 notes): Delta-aware OTM downside (needs fixture refactor), put-side `risk_drops_pct` semantics, `YuantaFetcher` empty-result raise. None of these can be safely done in a final-round 80-line budget.

## Proposed Changes

### 1. Replace English profile slugs with 中文 in backend `result.notes`

- **File**: `src/twse_warrant/analyzers/rank.py:209-286` (the `analyze_warrants` function — 4 `result.notes.append` call sites that all use `f"[{profile}] …"`)
- **Scope**: small (~6 lines: 1 dict literal + 4 f-string label edits + import line if needed)
- **Risk**: low — pure UI string change. The notes are display-only (`st.info(note)` consumer at `streamlit_app.py:301-302`). No tests assert exact note string content (`grep -n "stable\] " tests/` returns nothing).
- **Expected effect**: The two info banners shown directly above the header metric strip now read `[穩健型] 12 檔因缺 Greeks/IV 被排除` instead of `[stable] 12 檔因缺 Greeks/IV 被排除`. Closes the last visible English-slug leak; UI is fully Chinese after this.
- **Steps**:
  1. Near top of `rank.py` (after the existing imports, before `def _abs`), add:
     ```python
     PROFILE_LABELS_ZH: dict[Profile, str] = {
         "stable": "穩健型",
         "aggressive": "進攻型",
     }
     ```
  2. In `analyze_warrants`, replace each of the 4 occurrences of `f"[{profile}]` with `f"[{PROFILE_LABELS_ZH.get(profile, profile)}]`:
     - Line ~261: `f"[{profile}] 無權證符合過濾條件，改回傳成交量 Top 3"`
     - Line ~272: `f"[{profile}] 標的權證稀少，僅 {len(scored)} 檔通過過濾"`
     - Line ~282: `f"[{profile}] {excluded_greeks} 檔因缺 Greeks/IV 被排除"`
     - Plus the `if direction != "all"` empty-state on ~236 (uses `direction` not `profile`, no change there).
  3. Run `python3 -m pytest tests/ -q` — expect 32/32 pass (no test asserts the string).
  4. Restart Streamlit, run 2330 認購 + Yuanta. Visual: the two banners now read `[穩健型] 12 檔…` and `[進攻型] 12 檔…`.

### 2. Refresh README to cover R1–R4 features and correct the test count / user journey

- **File**: `README.md` (single file, ~30-40 line edit)
- **Scope**: medium — multiple small sections updated; no new top-level structure.
- **Risk**: low — documentation only; no code or test impact.
- **Expected effect**: A new reader visiting the repo on GitHub gets an accurate picture of what the app actually does today (情境模擬 + 等效Δ + Top-3 cards + 方向警示) instead of the R0-era "推薦表 + IV-Delta 散點圖" framing.
- **Steps** (line numbers refer to current README.md):
  1. **Line 25** — replace 「輸入標的 → 選方向 → 選風格 → 看推薦 + 候選表 + IV-Delta 散點圖」 with a more accurate flow:
     ```
     輸入標的 → 選方向（認購/認售） → 選資料來源 → （可選）啟用情境模擬 + 目標價 + 目標日期 → 看候選清單（依成交量排序）+ IV × |等效Δ| 散點圖 +（情境模式）達標報酬表 + Top-3 卡片
     ```
  2. **After line 25** — add a short subsection 「情境模擬」 explaining the target-price + days workflow (3-5 lines):
     ```
     #### 情境模擬（建議搭配 Yuanta）

     於側欄勾選「🎯 啟用情境模擬」，輸入目標標的價與目標日期（或天數）後重新分析，將額外得到：
     - 反推標的現價／目標價／預期漲跌幅 metric 列
     - 達標時的權證價、報酬率、損益兩平、平盤/跌5%/跌10% 風險情境
     - 達標報酬率 Top-3 卡片
     - 方向衝突警示：若認購搭配下跌目標、或認售搭配上漲目標，會提示換方向

     計算邏輯：權證達標價 = 目標日內含值 + 現有時間價值 × √(剩餘天數 / 現在天期)
     ```
  3. **Line 64** — under "中英欄名都支援" add one bullet:
     ```
     - 表頭顯示「等效Δ」（教科書 0~1 Delta），由原始 per-unit Delta ÷ 行使比例算得，方便跨權證比較跟漲能力。
     ```
  4. **Line 133** — replace 「20 個單元測試」 with 「32 個單元測試」.
  5. **Line 80, 推薦演算法重點** — keep table; add a one-line caveat below:
     ```
     > Streamlit UI 主畫面顯示通過硬過濾的「候選清單」聯集 + 散點圖 + （情境模式）達標報酬表，
     > 兩個 profile 的權重表只在過濾與評分階段使用，不再單獨顯示推薦表。
     ```
  6. No code changes; no tests to run. Quick verification: `wc -l README.md` (expect roughly +25-30 lines vs. current 142).

## Skipped (next time / human follow-up)

- **Delta-aware OTM downside** (R1#3 / R2 reverted / R3 / R4 deferred) — still highest-impact item but blocked on `tests/test_scenario.py:_call()` fixture refactor (per R3 review). Needs a dedicated dev session, not an overnight loop.
- **Put-side `risk_drops_pct` semantics** — `(0.0, -5.0, -10.0)` is misleading for puts; needs direction-aware tuple + dynamic column names. Cross-cuts `SCENARIO_COLUMN_CONFIG` keys; touches ~12 lines but high coordination cost.
- **`YuantaFetcher` raises on empty result** instead of returning `[]` for friendly empty state. Two-file fix (fetcher + streamlit handler).
- **達標報酬% column reorder** — column 14 of 16, off-screen on 1280px viewport. Pure UX call; same dilemma as R2/R3/R4.
- **Color-coding 漲跌幅% / 達標報酬%** — Streamlit `column_config` still has no per-cell color in current version.
- **README architecture diagram** (line 68-76) is still accurate; no edit needed.
