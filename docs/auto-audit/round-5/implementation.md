# Round 5 — FINAL ROUND Implementation Report

## Summary

| Item | Status |
|---|---|
| Item 1 — 中文 profile slugs in `result.notes` | ✅ Success |
| Item 2 — README refresh for R1–R4 features | ✅ Success |

**Success: 2 / 2**　**Failures: 0**　**Blockers: none**

---

## Item 1 — Replace English profile slugs with 中文

**File**: `src/twse_warrant/analyzers/rank.py`

### Changes
- Added `PROFILE_LABELS_ZH: dict[Profile, str] = {"stable": "穩健型", "aggressive": "進攻型"}` after the imports block.
- Replaced 3 call-site `[{profile}]` formatters with `[{PROFILE_LABELS_ZH.get(profile, profile)}]`:
  - `f"[{...}] 無權證符合過濾條件，改回傳成交量 Top 3"`
  - `f"[{...}] 標的權證稀少，僅 {len(scored)} 檔通過過濾"`
  - `f"[{...}] {excluded_greeks} 檔因缺 Greeks/IV 被排除"`

### Diff size
- Before: 287 lines → After: **292 lines** (+5)

### Verification
- `python -c "import ast; ast.parse(open('src/twse_warrant/analyzers/rank.py').read())"` → OK
- `pytest tests/ -q` → **32 passed** (no regressions)

---

## Item 2 — Refresh README.md to reflect R1–R4 features

**File**: `README.md`

### Changes
1. **User-flow line** updated to reference 認購/認售 + 資料來源 + 情境模擬 + 目標價/日期 + IV × |等效Δ| 散點圖 + 達標報酬表 + Top-3 卡片.
2. **New subsection 「情境模擬（建議搭配 Yuanta）」** added immediately after the user-flow line (within the Streamlit section) covering:
   - Sidebar checkbox `🎯 啟用情境模擬`
   - Reverse-derived spot / target / 預期漲跌幅 metrics
   - Risk scenarios (平盤 / 跌 5% / 跌 10%)
   - Top-3 達標報酬卡片
   - Direction-conflict warning
   - Pricing formula `權證達標價 = 目標日內含值 + 現有時間價值 × √(剩餘天數 / 現在天期)`
3. **CSV bullet list** appended:
   - `表頭顯示「等效Δ」（教科書 0~1 Delta），由原始 per-unit Delta ÷ 行使比例算得，方便跨權證比較跟漲能力。`
4. **測試 section**: `20 個單元測試` → `32 個單元測試`.
5. **推薦演算法重點 section**: caveat blockquote added after the weights table noting the UI shows the candidate union + scatter plot + scenario table, not separate per-profile recommendation tables.

### Diff size
- Before: 142 lines → After: **154 lines** (+12)

### Verification
- `pytest tests/ -q` → **32 passed**
- `wc -l README.md` → 154 (within expected 145–180 range)

---

## Streamlit & Visual Verification

- Streamlit restart: HTTP **200** at http://localhost:8765/
- Playwright flow:
  1. Navigated to http://localhost:8765
  2. Toggled sidebar `🎯 啟用情境模擬`
  3. Clicked `🔍 開始分析`
  4. Confirmed banners now read `[穩健型] 12 檔因缺 Greeks/IV 被排除` and `[進攻型] 12 檔因缺 Greeks/IV 被排除`
  5. Saved screenshot to `docs/auto-audit/round-5/screenshots-after/01-zh-banners.png`
  6. Closed browser

### Screenshot
- `/Users/KunYang/Claude/twse-warrant-analyzer/docs/auto-audit/round-5/screenshots-after/01-zh-banners.png`

---

## Test Counts

| Stage | Result |
|---|---|
| Baseline (before edits) | 32 / 32 passed |
| After Item 1 | 32 / 32 passed |
| After Item 2 (README only) | 32 / 32 passed |

---

## Files Modified

- `src/twse_warrant/analyzers/rank.py` (287 → 292 lines)
- `README.md` (142 → 154 lines)

No other files touched. No commit/push performed (parent will commit).
