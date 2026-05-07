# Handoff: 台股權證分析 — Warrant Analyzer (情境分析頁)

## Overview
單頁式台股權證分析工具的「分析後」狀態 UI。使用者輸入標的代碼、方向、目標價與目標日期，工具回傳「在這個情境下，哪些權證能獲利」的排序，並提供 Black-Scholes 合理價計算機輔助下單。

目標使用者：實際下單者（非機構）。痛點是盤口稀疏、心算合理價困難。設計目標是「下單前的決策面板」— 資訊密度高但不擁擠、數字優先、表格為主視覺。

## About the Design Files
本資料夾中的 HTML / JSX / CSS 檔案是 **設計參考稿**（in-browser React prototype with mock data），用來示範視覺、版面、互動意圖；**不是要直接部署的生產程式碼**。

實作任務是把這些設計搬進目標 codebase 既有的環境裡（Streamlit / Next.js / SwiftUI / Vue / 等等），沿用該專案的元件庫、資料層、狀態管理；如果還沒有專案環境，就選擇最適合的框架去重建。原始需求是 Streamlit `layout="wide"`，但本設計中許多細節（sticky 表頭、凍結欄、heatmap、Tweaks 面板）在 Streamlit 中不易做到 — 若要保留原 Streamlit，需以原生 widget 近似；若可選擇，建議用 React + 表格庫（TanStack Table / AG-Grid）+ Plotly 或 Recharts。

## Fidelity
**High-fidelity (hi-fi)**：色彩、字體、間距、陰影、圓角、Hover、過濾條件、表格欄位、計算機輸出皆已決定。請以像素級精度復刻。資料目前為 mock；接資料層時對應 `data.js` 內的欄位形狀。

---

## 設計語彙

- **整體風格**：現代金融 SaaS（Linear / Stripe 質感），淺色、清爽、低噪
- **色彩慣例**：台股 — 紅漲（`#d92d20`）/ 綠跌（`#079455`）。**不要套用美股慣例**
- **字體**：
  - Sans：`Geist` (Google Fonts, weight 300/400/500/600/700)
  - Mono：`Geist Mono` (weight 400/500/600)
  - Mono 用於：所有數字、代碼、日期、欄位輸入值
  - Sans 用於：標題、說明、欄位 label
  - 數字啟用 `font-variant-numeric: tabular-nums`（`.tnum` class）
- **資訊密度**：cozy（預設）。Tweaks 提供 compact / cozy / comfortable 三檔
- **不要**用 emoji 來代表狀態（綠勾✅、紅燈🔴 等可保留作 inline 強調，但 UI chrome 不依賴 emoji）

---

## Design Tokens

完整 token 在 `styles.css` 的 `:root` block。摘要：

### Colors
| Token | Hex | 用途 |
|---|---|---|
| `--bg` | `#fafaf9` | 頁面底色（warm off-white）|
| `--surface` | `#ffffff` | 卡片、輸入框 |
| `--surface-2` | `#f6f6f4` | 表頭、toolbar、輔助底 |
| `--surface-3` | `#efeeec` | 進階分層 |
| `--ink-1` | `#0a0a0a` | 主要文字 |
| `--ink-2` | `#404040` | 次要文字 |
| `--ink-3` | `#737373` | 輔助文字、label |
| `--ink-4` | `#a3a3a3` | placeholder、hint |
| `--line-1` | `#ececea` | 主分隔線 |
| `--line-2` | `#e3e2df` | 邊框、輸入框 |
| `--line-3` | `#d4d3cf` | 強分隔 |
| `--brand` | `#1d2540` | Logo、主要計算機卡 |
| `--accent` | `#ff5630` | CTA「開始分析」橘紅 |
| `--accent-hover` | `#ee4a23` | CTA hover |
| `--up` | `#d92d20` | 紅漲、認購、達標報酬 |
| `--up-bg` | `#fef2f0` | 紅淡底 |
| `--up-bg-2` | `#fde2dd` | 紅中底 |
| `--up-line` | `#f8b7ac` | 紅線條 |
| `--down` | `#079455` | 綠跌、認售、警示報酬 |
| `--down-bg` | `#effaf3` | 綠淡底 |
| `--down-bg-2` | `#d1f4dd` | 綠中底 |
| `--down-line` | `#95d6a8` | 綠線條 |

### Spacing / Radius / Shadow
- 圓角：`--r-sm: 6px` / `--r-md: 8px` / `--r-lg: 12px` / `--r-xl: 16px`
- 容器水平 padding：`32px`，max-width `1440px`
- 主陰影：`0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.04)`（卡片 `--shadow-xs/sm/md/lg`）

### Type
- 頁標 H1：26px / 600 / `-0.02em`
- 區塊標題 H2：17px / 600 / `-0.01em`
- KPI 數字：28px / 600 / Geist Mono / `-0.02em`
- 排名#1 報酬數字：36px / 700 / Geist Mono
- 表格內文：12.5px / Geist Mono
- 表頭：11.5px / 500 / uppercase / `0.06em` letter-spacing
- 欄位 label：11.5px / 500 / uppercase / `0.06em`

---

## Page Structure (top → bottom)

### 1. Top Bar (sticky, h=60px)
- 左：Logo（28×28 漸層深藍方塊內含上揚折線 SVG）+「台股權證分析」+ 「Warrant Analyzer」副標
- 右：市場開盤狀態 pill（綠色，含脈衝點 + 時間）/ 資料來源 / 更新時間 / 「歷史紀錄」次要按鈕
- 背景：`rgba(255,255,255,0.85)` + `backdrop-filter: saturate(180%) blur(12px)`

### 2. Page Head
- H1「情境分析 — 2330 台積電」（標的隨輸入動態更新）
- 副標說明工具用途

### 3. Input Card
- 6 欄 grid（`1.05fr 1.15fr 0.85fr 1fr 1.15fr 1fr`）：
  1. 標的代碼 — text input + 後綴顯示中文名（「台積電」）
  2. 方向 — segmented control（認購紅 / 認售綠），active 端會帶該色文字
  3. Top N — slider 3~10，預設 5，下方顯示刻度
  4. 目標標的價 — number input，前綴 `NT$`
  5. 目標達成日期 — date input，label hint 顯示「距今 60 日」
  6. 「開始分析」CTA — `--accent` 橘紅，full width，含放大鏡 icon
- 下方一行 caption：資料來源 / 漲跌色慣例提示 / 鍵盤快捷鍵（`/` 聚焦、`⏎` 分析）+ 右側「儲存策略」「重設」次要按鈕

### 4. KPI Grid (4 cards)
- 反推標的現價 / 目標價 / **預期漲跌幅（accent 卡，淺橘漸層底）** / 候選池
- 每張卡：label（uppercase 11.5px）+ 大數字（28px Mono）+ meta 行（含趨勢箭頭）
- 預期漲跌幅有特殊 accent 樣式：`linear-gradient(180deg, #fef6f3 0%, #ffffff 60%)`、`border-color: #ffd9ce`

### 5. Filter Status
- 過濾條件 chip 列：到期早於目標日 5 / 成交量不足 99 / 價差過寬 40 / 達標仍虧損 17 / 缺 Greeks/IV 4
- 綠色 status bar：「✅ 通過情境過濾：78 檔　按達標報酬率排序」+ 右側耗時 metadata

### 6. Section: 🎯 情境模擬 — Top 3 Podium
- 3 欄不等寬：`1.35fr 1fr 1fr`，#1 卡較寬、報酬數字 36px
- 每張卡：
  - 頂部 4px ribbon — #1 紅漸層、#2 銀灰漸層、#3 銅金漸層
  - #1 卡 body 為 `linear-gradient(180deg, #fff8f5 0%, #ffffff 50%)` 帶橘色邊
  - 排名數字徽（22×22 圓角 6px，#1 紅 / #2 灰 / #3 棕底）
  - 達標報酬大字（red, mono, weight 700）
  - 權證代碼（mono 16px 600）+ 名稱
  - 6 列 KV grid（履約/天期、行使比例、現價→預期、損益兩平、等效Δ·IV、槓桿）
  - 底部 3 格警示（綠底）— 平盤不動 / 跌 5% / 跌 10% 報酬

### 7. Section: 完整情境表
- Sticky header + 凍結左二欄（權證代碼、權證名稱）
- 17 欄；達標報酬 / 平盤 / 跌 5% / 跌 10% 四欄為 **heatmap cell**（`<span class="hm">`）：
  - 紅漸層：`rgba(217, 45, 32, 0.06 ~ 0.55)`，按 `value / 350` 線性
  - 綠漸層：`rgba(7, 148, 85, 0.06 ~ 0.40)`，按 `|value| / 100` 線性
  - 強度 > 0.55 文字轉白
- 前 3 列 row 加 `.highlight` class（淡橘漸層底）
- Toolbar：搜尋框（含 SVG 放大鏡 inline-svg as background-image）/ 顯示筆數 / 排序狀態 / 篩選按鈕 / 匯出 CSV

### 8. Section: 合理價計算機
- 卡片標題列含 26×26 深藍方形 icon
- Tabs：「從候選清單選」「手動輸入」
- 兩欄 body（`1.1fr 1fr`，中間分隔線）：
  - 左：輸入區
    - List 模式：select 下拉
    - Manual 模式：兩列 3 欄（方向 segmented / 履約 / 行使比例 ; 剩餘天數 / 市價 / IV%）
    - 共用區：3 欄（現在標的價 / IV% slider / 步長）+ 2 欄（無風險利率 slider / 股息率 slider）
  - 右：輸出區（淡灰→白漸層底）
    - 3 卡：BS 合理價（深藍 primary，28px Mono 白字）/ 買進可掛（綠數字）/ 賣出可掛（紅數字）
    - meta line：市價 / 偏差 % / 內含值 + 時間價值 / 到期天數
    - 敏感度表 7 列（−3× ~ +3×），中間 0 列高亮

### 9. Section: 🗂️ 候選清單（Tweaks 可關）
- 16 欄 dataframe，類型欄為 tag（購紅 / 售綠）
- segmented filter（全部 / 認購 / 認售），active 帶對應色
- 凍結左二欄

### 10. Section: 📊 候選分佈散佈圖
- 自繪 SVG 散佈圖（不依賴 chart 庫）
  - x 軸 IV %（20~60），y 軸 |等效Δ|（0~1）
  - 點半徑 = `4 + sqrt(vol/maxVol) * 14`
  - 點顏色 = Viridis 5 色（紫→藍→青→綠→黃）按 `(lev - minLev) / (maxLev - minLev)` 線性內插
  - 高亮區：右上「深價內 · 高 IV」（紅淡底矩形）
  - 點 stroke 1px 白
- 圖例：Viridis bar（100×8 圓角）+ 三圈大小示意

### 11. Section: 個別權證資料
- 卡片頂部 select 切換 + 右側標籤（購）+ 履約 + 剩餘
- 兩欄 body（中間分隔線）：基本資料 / Greeks·隱波·槓桿，每欄 KV grid（左 sans 灰、右 mono 黑右對齊）

### 12. Logic Expander
- `<details>` 折疊區，預設收合
- 列出等效 Delta / 達標權證價 / 拆解 / 損益兩平 / tick 對齊定義

### 13. Footer
- 12px 灰字 — 設計稿聲明 + 版本 + 資料來源

---

## Interactions

- **Hover**：表格列 → `--surface-2`；按鈕 → 變底；CTA → `--accent-hover`
- **Focus**：input 有 `box-shadow: 0 0 0 3px rgba(29,37,64,0.08)` + 邊框轉深
- **Active CTA press**：`transform: translateY(1px)` 微凹陷
- **Sliders**：白底圓 thumb + 深藍 2px 邊 + 小陰影
- **Sticky 表頭/欄**：列 hover 時 sticky cell 也要同步轉底色（CSS 已處理）
- **Tweaks Panel**：右下浮動，可拖拉，主機 toolbar 切換顯示

---

## State Management

預期 state（在最終 codebase 中）：
- `form`：標的代碼 / 方向 / topN / 目標價 / 目標日期
- `analysisRun`：是否已執行（決定 KPI / 表格 / Top3 是否顯示；本稿假設 post-analysis 狀態）
- `selectedWarrant`（計算機）：from list 模式選中的代碼
- `bsInputs`：iv / step / r / q / 標的現價（共用）
- `manualInputs`（manual 模式）：方向、履約、行使比例、剩餘、市價、IV
- `tableFilters`：候選表 type filter（call/put/all）+ 搜尋字串
- `detailCode`：個別權證面板選中的代碼

資料 fetching：
- 元大權證網（或內部 mirror）抓全市場 ~942 檔權證的 snapshot
- 後端依方向 / 目標價 / 目標日期執行情境模擬，回傳 78 檔通過 + 報酬欄位
- BS 計算前端執行（避免每個 slider 動作都打後端）— 若太重可後端，或前端 worker

---

## Files in this bundle

| File | 用途 |
|---|---|
| `Warrant Analyzer.html` | 入口 HTML，掛 React + Babel + 五個 JSX |
| `styles.css` | 完整 design tokens + 元件樣式 |
| `data.js` | Mock 資料生成（情境表 20 列 + 候選表 36 列）|
| `parts-1.jsx` | TopBar / PageHead / InputRow / KpiRow / TopCards / FilterStatus + helpers |
| `parts-2.jsx` | ScenarioTable / CandidateTable / BSCalculator |
| `parts-3.jsx` | ScatterChart (自繪 SVG) / DetailPanel / LogicExpander |
| `app.jsx` | 主 App 組裝 + Tweaks 面板 |
| `tweaks-panel.jsx` | Tweaks 面板 starter（可丟棄，僅用於原型互動）|
| `original-design-brief.md` | 原始需求文件 |

實作時可忽略 `tweaks-panel.jsx`（僅原型用）；`data.js` 可以對照欄位形狀做 API 規格。

---

## Notes

- 紅漲綠跌是台股慣例 — 全球設計中極少見，**請務必確認 codebase 沒有自動把「正數=綠」當預設**
- Heatmap 強度公式可調 — 目前 max scale 是 350%（達標報酬），實務上偶有破 500% 的權證會超出色階；可改為動態 quantile
- 散佈圖如果改用 Plotly，注意把 marker color 設為 Viridis、`marker.line.color=white`、`marker.line.width=1` 才能還原視覺
- 行動裝置版面未設計 — 桌機優先；若要支援，建議 < 1024px 時 stack input row、KPI 改 2 欄、Top 3 改 stack
