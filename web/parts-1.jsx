/* global React */
const { useState, useMemo } = React;

// ============================================================
// Helpers
// ============================================================
const fmt = (n, d = 2) => {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
};
const pct = (n, d = 1) => (n >= 0 ? '+' : '') + fmt(n, d) + '%';
const sign = (n) => n > 0 ? 'up' : n < 0 ? 'down' : '';

// Heatmap color for return %
function heatBg(v, max = 350) {
  if (v >= 0) {
    const t = Math.min(1, v / max);
    // light → strong red
    const a = 0.06 + t * 0.55;
    return { background: `rgba(217, 45, 32, ${a})`, color: t > 0.55 ? '#ffffff' : '#7a1410' };
  } else {
    const t = Math.min(1, Math.abs(v) / 100);
    const a = 0.06 + t * 0.40;
    return { background: `rgba(7, 148, 85, ${a})`, color: t > 0.6 ? '#ffffff' : '#054f31' };
  }
}

// ============================================================
// Header
// ============================================================
function TopBar() {
  return (
    <header className="topbar">
      <div className="container topbar-inner">
        <div className="brand">
          <div className="brand-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3,17 9,11 13,15 21,7" />
              <polyline points="14,7 21,7 21,14" />
            </svg>
          </div>
          <div className="brand-name">
            台股權證分析<span className="sub">Warrant Analyzer</span>
          </div>
        </div>
        <div className="topbar-right">
          <span className="status-pill"><span className="dot"></span>市場開盤中 · 13:24:51</span>
          <span>資料 <strong style={{color:'var(--ink-1)', fontWeight:500}}>yuanta</strong></span>
          <span className="dot-sep">·</span>
          <span>更新於 14:30</span>
          <button className="btn btn-sm">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/><path d="M12 6v6l4 2"/></svg>
            歷史紀錄
          </button>
        </div>
      </div>
    </header>
  );
}

// ============================================================
// Page head
// ============================================================
function PageHead() {
  return (
    <div className="page-head">
      <h1 className="page-title">情境分析 — 2330 台積電</h1>
      <p className="page-sub">輸入標的、目標價與目標日期，工具回傳「在這個情境下，哪些權證能獲利」並排序。</p>
    </div>
  );
}

// ============================================================
// Input row
// ============================================================
function InputRow({ form, setForm }) {
  const [topN, setTopN] = useState(form.topN);
  return (
    <div className="input-card">
      <div className="input-row">
        <div>
          <label className="field-label">標的代碼</label>
          <div className="input-wrap">
            <input className="input mono" defaultValue="2330" />
            <div className="input-suffix">台積電</div>
          </div>
        </div>

        <div>
          <label className="field-label">方向</label>
          <div className="seg" role="radiogroup">
            <button className={`active up`}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="6,15 12,9 18,15"/></svg>
              認購 Call
            </button>
            <button>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="6,9 12,15 18,9"/></svg>
              認售 Put
            </button>
          </div>
        </div>

        <div>
          <label className="field-label">Top N <span className="slider-value mono">{topN}</span></label>
          <div className="slider-wrap">
            <input type="range" min="3" max="10" value={topN} onChange={e => setTopN(+e.target.value)} className="slider" />
            <div className="slider-row"><span>3</span><span>5</span><span>10</span></div>
          </div>
        </div>

        <div>
          <label className="field-label">目標標的價</label>
          <div className="input-wrap">
            <div className="input-prefix">NT$</div>
            <input className="input mono with-prefix" defaultValue="2,800.00" />
          </div>
        </div>

        <div>
          <label className="field-label">目標達成日期 <span className="hint">距今 60 日</span></label>
          <div className="input-wrap">
            <input className="input mono" defaultValue="2026-07-06" />
            <div className="input-suffix">📅</div>
          </div>
        </div>

        <div>
          <button className="btn btn-primary" style={{width:'100%'}}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            開始分析
          </button>
        </div>
      </div>

      <div className="cta-row">
        <div className="cta-meta">
          <span>資料來源：元大權證網</span>
          <span className="sep">·</span>
          <span>台股慣例：<span style={{color:'var(--up)', fontWeight:600}}>紅漲</span> / <span style={{color:'var(--down)', fontWeight:600}}>綠跌</span></span>
          <span className="sep">·</span>
          <span>快捷：<span className="kbd">/</span> 聚焦輸入　<span className="kbd">⏎</span> 分析</span>
        </div>
        <div style={{display:'flex', gap:8}}>
          <button className="btn btn-ghost btn-sm">儲存策略</button>
          <button className="btn btn-sm">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M3 21v-5h5"/></svg>
            重設
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// KPI
// ============================================================
function KpiRow() {
  return (
    <div className="kpi-grid section">
      <div className="kpi">
        <div className="kpi-label">反推標的現價</div>
        <div className="kpi-value tnum">2,310<span className="unit">.00</span></div>
        <div className="kpi-meta">
          <span className="trend up arrow-up">12.50</span>
          <span>· 前收 2,297.50</span>
        </div>
      </div>
      <div className="kpi">
        <div className="kpi-label">目標價（60 天後）</div>
        <div className="kpi-value tnum">2,800<span className="unit">.00</span></div>
        <div className="kpi-meta">2026-07-06 達成</div>
      </div>
      <div className="kpi accent">
        <div className="kpi-label">預期漲跌幅</div>
        <div className="kpi-value tnum" style={{color:'var(--up)'}}>+21.21<span className="unit">%</span></div>
        <div className="kpi-meta">
          <span className="trend up arrow-up">490.00 點</span>
        </div>
      </div>
      <div className="kpi">
        <div className="kpi-label">候選池</div>
        <div className="kpi-value tnum">942<span className="unit"> 檔</span></div>
        <div className="kpi-meta">
          <span style={{color:'var(--down)'}}>● 通過硬過濾 239</span>
          <span>·</span>
          <span style={{color:'var(--up)'}}>● 通過情境 78</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Top 3 cards (Podium)
// ============================================================
function TopCards({ rows }) {
  const top3 = rows.slice(0, 3);
  return (
    <div className="podium">
      {top3.map((r, i) => (
        <div className={`rank-card r${i+1}`} key={r.code}>
          <div className="ribbon"></div>
          <div className="rank-head">
            <div className="rank-no">
              <span className="num">{i+1}</span>
              <span>達標報酬排序</span>
            </div>
            <div className="rank-return">
              <div className="label">達標報酬</div>
              <div className="value">+{fmt(r.ret, 1)}%</div>
            </div>
          </div>

          <div className="rank-id">
            <div className="code">{r.code}</div>
            <div className="name">{r.name}</div>
          </div>

          <div className="rank-grid">
            <div className="rg-row"><span className="k">履約 / 天期</span><span className="v">{fmt(r.strike,0)} / {r.days}d</span></div>
            <div className="rg-row"><span className="k">行使比例</span><span className="v">{r.ratio.toFixed(4)}</span></div>
            <div className="rg-row"><span className="k">現價 → 預期</span><span className="v">{fmt(r.price)} → <span style={{color:'var(--up)'}}>{fmt(r.targetPx)}</span></span></div>
            <div className="rg-row"><span className="k">損益兩平</span><span className="v">{fmt(r.be,0)} <span style={{color:'var(--ink-3)', fontSize:'11px'}}>(+{fmt(((r.be-2310)/2310)*100, 1)}%)</span></span></div>
            <div className="rg-row"><span className="k">等效Δ · IV</span><span className="v">{r.delta.toFixed(2)} · {r.iv.toFixed(0)}%</span></div>
            <div className="rg-row"><span className="k">槓桿</span><span className="v">{r.lev.toFixed(1)}x</span></div>
          </div>

          <div className="rank-warn">
            <div className="warn-cell">
              <div className="label">平盤不動</div>
              <div className="value">{fmt(r.flatRet,1)}%</div>
            </div>
            <div className="warn-cell">
              <div className="label">跌 5%</div>
              <div className="value">{fmt(r.d5,1)}%</div>
            </div>
            <div className="warn-cell">
              <div className="label">跌 10%</div>
              <div className="value">{fmt(r.d10,1)}%</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================
// Scenario filter status
// ============================================================
function FilterStatus() {
  return (
    <>
      <div className="chips">
        <span className="chip">過濾條件</span>
        <span className="chip dim">到期早於目標日 <strong>5</strong></span>
        <span className="chip dim">成交量不足 <strong>99</strong></span>
        <span className="chip dim">價差過寬 <strong>40</strong></span>
        <span className="chip dim">達標仍虧損 <strong>17</strong></span>
        <span className="chip dim">缺 Greeks/IV <strong>4</strong></span>
      </div>
      <div className="status-bar">
        <div className="check">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20,6 9,17 4,12"/></svg>
        </div>
        <div>
          <strong>通過情境過濾：78 檔</strong>　
          按達標報酬率排序
        </div>
        <span style={{flex:1}}></span>
        <span className="meta">耗時 0.42s · BS 重定價 78 次</span>
      </div>
    </>
  );
}

window.WAComponents = { TopBar, PageHead, InputRow, KpiRow, TopCards, FilterStatus, fmt, pct, sign, heatBg };
