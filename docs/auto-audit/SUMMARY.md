# Auto-Audit Overnight Loop — Summary

**Target end**: 2026-05-07 06:00 Asia/Taipei
**Branch**: main (commit + push directly)
**Process**: every hour, review agent + implementation agent

| Round | Time (TW) | Status | Commit | Files | Notes |
|---|---|---|---|---|---|
| 1 | 2026-05-07 00:30 | ✅ success | `7f82baf` | streamlit_app.py | 等效Δ 顯示 + 情境表 tooltip + 重複風險警示 |
| 2 | 2026-05-07 01:45 | ⚠️ partial | `cd19da9` | streamlit_app.py | 候選表 default sort by 成交量↓；Delta-aware OTM 模型 reverted（test fixture Delta 不真實，需先 refactor）|
| 3 | 2026-05-07 03:05 | ✅ success | `8c17e63` | streamlit_app.py | Header 加標的現價/目標/預期漲跌幅 metric；3 卡片重複 caption 收斂為 1 條；底部 Mock 隨機走勢圖 gate Mock-only |
| 4 | 2026-05-07 04:25 | ✅ success | `0464e7a` | streamlit_app.py | 進階閾值 expander 中文化；call/put 方向 vs target 衝突警示；sidebar 加 2 條 divider |
| 5 | 2026-05-07 05:45 | ✅ success | `4701b41` | rank.py + README.md | 後端 `result.notes` 從 `[stable]` 換成 `[穩健型]`；README 補上 R1-R4 新增功能 |

## Round details

### Round 1 — 2026-05-07 00:30
- Review proposed 3 items, picked 1+2 (small/low-risk)
- Item A: 候選表 Delta → 等效Δ；bubble chart 同步
- Item B: 情境表 12 欄加 tooltip；三檔風險相同時加 caption
- Skipped #3 (Delta-aware OTM model) — medium risk，留下輪
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-1/{review.md, implementation.md, screenshots/, screenshots-after/}`

### Round 2 — 2026-05-07 01:45
- Review picked 2 items (Round 1 skipped #3 + new sort)
- Item A (Delta-aware OTM downside): **REVERTED**。公式正確但測試 fixture `_call()` 用 `delta=0.5`（不真實，實際 per-unit Δ ~0.002），導致：
  - 新 test 因 delta_shadow 太大被 clamp 到 -100% 不嚴格遞減
  - 既有 test_evaluate_scenarios_filters_and_sorts 因虛擬 delta 過大讓「不該獲利」的 case 變獲利
  - 解法：先 refactor test fixture 用 `equivalent_delta × ratio` 反推真實 per-unit delta，再開 Item A
- Item B (default sort 成交量↓): ✅ 成功。候選表最高量在頂端，使用者仍可點 header 自排
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-2/{review.md, implementation.md, screenshots*/}`

### Round 3 — 2026-05-07 03:05
- Review proposed 3 small items, picked 全部 3 個（risk 都低）
- Item 1: Top-3 卡片內重複 3 次的「三檔風險情境報酬相同」caption → 改成單一 `st.info` 顯示在卡片區上方
- Item 2: 結果頁頂部加 3-column metric（反推標的現價、目標價、預期漲跌幅%），免捲動就看到情境關鍵資訊
- Item 3: 底部合成走勢圖（spot_path = 1100 + ...）gate 在 Mock 來源；yuanta/TWSE/CSV 不再顯示
- Skipped (留下輪): Delta-aware OTM 仍待 fixture refactor；put 方向的 risk_drops_pct 標籤誤導；yuanta 0 結果 raise → 友善 empty state
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-3/{review.md, implementation.md, screenshots*/}`

### Round 4 — 2026-05-07 04:25
- Review proposed 3 小範圍低風險的改進，全做
- Item 1: 進階：硬過濾閾值 expander 把 `stable`/`aggressive` 英文 slug 換成「穩健型」/「進攻型」中文（widget keys 保留英文以維持 state identity）
- Item 2: 情境模擬 metric 後加方向衝突警示——「call + 目標 < 現價」或「put + 目標 > 現價」時提示使用者考慮換方向
- Item 3: sidebar 加兩條 `st.divider()` 把版面分為標的/情境/進階/開始分析 四組
- Skipped (留下輪): Delta-aware OTM（仍待 fixture refactor）；put-side risk_drops_pct 語義；yuanta empty result 友善 empty state；README 補上等效Δ/情境模擬說明
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-4/{review.md, implementation.md, screenshots*/}`

### Round 5 (FINAL) — 2026-05-07 05:45
- 收尾輪，挑 2 個 wrap-up items
- Item 1: `rank.py:analyze_warrants` 的 `result.notes` 從 `[stable] 12 檔...` / `[aggressive] 12 檔...` 換成 `[穩健型] 12 檔...` / `[進攻型] 12 檔...`，UI banner 不再夾雜英文（R4 做了 expander 部分但 notes 是 rank.py 的，留到 R5 收尾）
- Item 2: README 從 R0 後沒更新，補上：等效Δ、情境模擬、反推現價 metric、方向警示、預設 sort 成交量↓；使用流程描述對齊現況；測試數 20 → 32
- Skipped (人工收尾): Delta-aware OTM（仍待 fixture refactor）；put-side risk_drops_pct 語義；yuanta empty result 友善 empty state
- pytest 32/32, Streamlit HTTP 200
- Files: `docs/auto-audit/round-5/{review.md, implementation.md, screenshots*/}`

---

## 🌅 Final Wrap-up — Overnight Loop 結束

**運行時間**：2026-05-07 00:30 → 05:55 Asia/Taipei（5 輪，總時數 5h25m）

**累積成果**：
- **commits 推到 main**: 10 個（5 個 changes + 5 個 SUMMARY 更新）
- **檔案改動**: 主要為 `src/streamlit_app.py`、`src/twse_warrant/analyzers/rank.py`、`README.md`
- **新增測試**: 0 個（每輪都保持 32/32 不破壞既有 test）
- **revert 次數**: 1（R2 Item A — Delta-aware OTM 公式對但 fixture 不真實）

**已 ship 的改進清單**：
1. R1: 候選表 Delta → 等效Δ；bubble chart 同步使用 equivalent_delta
2. R1: 情境表 12 欄加 tooltip；三檔風險相同時 caption 警示
3. R2: 候選表預設依成交量降序排序
4. R3: 收斂 Top-3 卡片重複 caption → 單一 info 顯示在卡片區上方
5. R3: 結果頁頂部加 3-column metric（反推現價/目標/預期漲跌幅）
6. R3: 底部 Mock 隨機走勢圖 gate 在 Mock 來源
7. R4: 進階閾值 expander 英文 slug 中文化
8. R4: 情境模擬方向衝突警示（call+target<spot / put+target>spot）
9. R4: sidebar 加 2 條 divider 視覺分組
10. R5: rank.py result.notes 中文化（最後一個英文 slug leak）
11. R5: README 從 R0 過時狀態補上 R1-R4 所有新功能

**仍需人工處理的 backlog**：
1. **Delta-aware OTM downside model**（最高優先）：Top-3 卡片的「平盤/-5%/-10%」三檔報酬目前對深 OTM 權證會顯示相同數字（純時間衰減）。需先 refactor `tests/test_scenario.py:_call()` 用真實 per-unit Delta（≈ ratio × textbook Δ），再加 `eq_delta × ΔS × ratio` 項到 `_project_warrant_price` 的 `intrinsic_target == 0` 分支。R2 嘗試過但 fixture 假設不真實導致 revert；需要一個專注的 dev session
2. **Put-side `risk_drops_pct` 語義**：認售情境下 `(0.0, -5.0, -10.0)` 是 tailwind 不是風險。修法：put 用 `(0.0, +5.0, +10.0)` 並動態改 column 名「漲5%報酬%」「漲10%報酬%」。跨 SCENARIO_COLUMN_CONFIG keys 與 risk_returns 字典 lookup
3. **YuantaFetcher empty result raise → 友善 empty state**：目前抓到 0 檔會丟 exception 而非 return []。fetcher class + streamlit error handler 兩處
4. **達標報酬% column 位置**：scenario 表 14/16 欄，1280px 視窗會落在折頁外。要重新排欄位順序
5. **色彩編碼漲跌幅% / 達標報酬%**：Streamlit `column_config.NumberColumn` 還沒支援 per-cell color；要等版本更新或用 `pd.Styler`（會失去 pinned 欄位）

**早晨 next steps 建議**：
1. 先 `git log --oneline -15` 看一下這 10 個 auto-audit commits
2. 開 http://localhost:8765 跑 2330 認購 + 情境模擬 看現況
3. 對照 `docs/auto-audit/round-N/screenshots-after/` 看每輪視覺差別
4. 不滿意某輪：`git revert <hash>` 回退單一輪（commits hash 已記在表格）
5. 若要繼續做 backlog #1（Delta-aware OTM）：建議先用 30 分鐘專心 refactor test fixture

