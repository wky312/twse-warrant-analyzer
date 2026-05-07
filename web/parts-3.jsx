/* global React */
const { fmt: fmt3 } = window.WAComponents;
const { useState: useS3 } = React;

// ============================================================
// Scatter — IV × |Δ|, size=vol, color=lev (Viridis)
// ============================================================
function viridis(t) {
  // simple 5-stop viridis approximation
  const stops = [
    [68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]
  ];
  t = Math.max(0, Math.min(1, t));
  const idx = t * (stops.length - 1);
  const i = Math.floor(idx);
  const f = idx - i;
  const a = stops[i];
  const b = stops[Math.min(stops.length - 1, i + 1)];
  const r = Math.round(a[0] + (b[0] - a[0]) * f);
  const g = Math.round(a[1] + (b[1] - a[1]) * f);
  const bl = Math.round(a[2] + (b[2] - a[2]) * f);
  return `rgb(${r},${g},${bl})`;
}

function ScatterChart({ rows }) {
  const W = 1200, H = 360;
  const padL = 56, padR = 24, padT = 16, padB = 44;
  const xMin = 20, xMax = 60;
  const yMin = 0, yMax = 1;
  const sx = v => padL + ((v - xMin) / (xMax - xMin)) * (W - padL - padR);
  const sy = v => H - padB - ((v - yMin) / (yMax - yMin)) * (H - padT - padB);

  const xt = [20, 30, 40, 50, 60];
  const yt = [0, 0.25, 0.5, 0.75, 1.0];
  const maxLev = Math.max(...rows.map(r => r.lev));
  const minLev = Math.min(...rows.map(r => r.lev));
  const maxVol = Math.max(...rows.map(r => r.vol));

  return (
    <div className="scatter-card">
      <div className="section-head" style={{margin:0}}>
        <div>
          <div className="section-title">候選分佈：IV × |等效Δ|</div>
          <div className="section-sub">每個氣泡為一檔權證；大小 = 成交量、顏色 = 實質槓桿（Viridis）</div>
        </div>
        <div className="legend">
          <span className="legend-grad">
            <span style={{color:'var(--ink-3)'}}>低槓桿</span>
            <span className="bar2"></span>
            <span style={{color:'var(--ink-3)'}}>高槓桿</span>
          </span>
          <span style={{display:'inline-flex', alignItems:'center', gap:8}}>
            <svg width="40" height="14"><circle cx="6" cy="7" r="3" fill="var(--ink-3)" opacity="0.5"/><circle cx="20" cy="7" r="6" fill="var(--ink-3)" opacity="0.5"/><circle cx="34" cy="7" r="9" fill="var(--ink-3)" opacity="0.5"/></svg>
            <span style={{color:'var(--ink-3)'}}>成交量</span>
          </span>
        </div>
      </div>
      <div className="scatter-area">
        <svg className="scatter-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          {/* gridlines */}
          {yt.map(v => (
            <g key={'y'+v}>
              <line x1={padL} x2={W-padR} y1={sy(v)} y2={sy(v)} stroke="var(--line-1)" strokeDasharray={v===0?undefined:'2 4'} />
              <text x={padL-10} y={sy(v)+4} fontSize="11" fill="var(--ink-3)" textAnchor="end" fontFamily="Geist Mono">{v.toFixed(2)}</text>
            </g>
          ))}
          {xt.map(v => (
            <g key={'x'+v}>
              <line y1={padT} y2={H-padB} x1={sx(v)} x2={sx(v)} stroke="var(--line-1)" strokeDasharray={v===xMin?undefined:'2 4'} />
              <text y={H-padB+18} x={sx(v)} fontSize="11" fill="var(--ink-3)" textAnchor="middle" fontFamily="Geist Mono">{v}%</text>
            </g>
          ))}
          {/* axis labels */}
          <text x={(padL + W - padR)/2} y={H-6} fontSize="11.5" fill="var(--ink-3)" textAnchor="middle">隱含波動度 IV %</text>
          <text x={14} y={(padT + H - padB)/2} fontSize="11.5" fill="var(--ink-3)" textAnchor="middle" transform={`rotate(-90, 14, ${(padT + H - padB)/2})`}>|等效 Δ|</text>

          {/* highlight zones */}
          <rect x={sx(40)} y={sy(0.7)} width={sx(60)-sx(40)} height={sy(0.3)-sy(0.7)} fill="var(--up-bg)" opacity="0.4"/>
          <text x={sx(50)} y={sy(0.95)+4} fontSize="10" fill="var(--up)" textAnchor="middle" opacity="0.8" fontWeight="500">深價內 · 高 IV</text>

          {/* points */}
          {rows.map((r) => {
            const t = (r.lev - minLev) / (maxLev - minLev || 1);
            const radius = 4 + Math.sqrt(r.vol / maxVol) * 14;
            return (
              <circle key={r.code}
                cx={sx(r.iv)} cy={sy(r.delta)}
                r={radius}
                fill={viridis(t)}
                opacity="0.78"
                stroke="white"
                strokeWidth="1"
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}

// ============================================================
// Detail Panel
// ============================================================
function DetailPanel({ rows }) {
  const [code, setCode] = useS3(rows[0].code);
  const w = rows.find(r => r.code === code) || rows[0];
  return (
    <div className="detail-card">
      <div className="detail-head">
        <div style={{display:'flex', alignItems:'center', gap:12}}>
          <div className="section-title" style={{fontSize:14}}>個別權證資料</div>
          <select className="input mono" value={code} onChange={e=>setCode(e.target.value)} style={{height:32, fontSize:12.5, width:280}}>
            {rows.map(r => <option key={r.code} value={r.code}>{r.code} · {r.name}</option>)}
          </select>
        </div>
        <div style={{display:'flex', gap:8, alignItems:'center', fontSize:12.5, color:'var(--ink-3)'}}>
          <span className="tag call">購</span>
          <span>履約 <strong style={{color:'var(--ink-1)'}} className="mono">{fmt3(w.strike,0)}</strong></span>
          <span className="dot-sep">·</span>
          <span>剩餘 <strong style={{color:'var(--ink-1)'}} className="mono">{w.days}d</strong></span>
        </div>
      </div>
      <div className="detail-body">
        <div className="detail-col">
          <h4>基本資料</h4>
          <div className="kv">
            <span className="k">上市日期</span><span className="v">2024-08-15</span>
            <span className="k">最後交易日</span><span className="v">2026-09-{(10 + (w.days % 20)).toString().padStart(2,'0')}</span>
            <span className="k">到期日期</span><span className="v">2026-09-{(12 + (w.days % 18)).toString().padStart(2,'0')}</span>
            <span className="k">發行型態</span><span className="v">歐式 · 現金結算</span>
            <span className="k">最新發行張數</span><span className="v">{(8000 + w.vol*3).toLocaleString()}</span>
            <span className="k">流通比例</span><span className="v">{(15 + (w.delta * 30)).toFixed(2)}%</span>
            <span className="k">最新履約價</span><span className="v">{fmt3(w.strike,0)}</span>
            <span className="k">行使比例</span><span className="v">{w.ratio.toFixed(4)}</span>
          </div>
        </div>
        <div className="detail-col">
          <h4>Greeks · 隱波 · 槓桿</h4>
          <div className="kv">
            <span className="k">買價隱波</span><span className="v">{(w.iv - 0.6).toFixed(1)}%</span>
            <span className="k">賣價隱波</span><span className="v">{(w.iv + 0.8).toFixed(1)}%</span>
            <span className="k">原始 Delta</span><span className="v">{(w.delta * w.ratio * 100).toFixed(4)}</span>
            <span className="k">等效 Delta</span><span className="v">{w.delta.toFixed(3)}</span>
            <span className="k">Theta</span><span className="v" style={{color:'var(--down)'}}>−{(0.004 + Math.random()*0.012).toFixed(4)}</span>
            <span className="k">剩餘天數</span><span className="v">{w.days} 日</span>
            <span className="k">價內外程度</span><span className="v">{(w.moneyness>=0?'+':'')+w.moneyness.toFixed(2)}%</span>
            <span className="k">實質槓桿</span><span className="v">{w.lev.toFixed(2)}×</span>
            <span className="k">買賣價差比</span><span className="v">{(0.5 + Math.random()*2.5).toFixed(2)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Logic expander
// ============================================================
function LogicExpander() {
  return (
    <details className="expander">
      <summary>
        <span style={{display:'inline-flex', alignItems:'center', gap:8}}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          計算邏輯與 Delta 說明
        </span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6,9 12,15 18,9"/></svg>
      </summary>
      <div className="body">
        <p><strong>等效 Delta：</strong>等效 Δ = 原始 Δ ÷ 行使比例。教科書 0~1 標準化的 Delta，方便跨權證比較。</p>
        <p><strong>達標權證價：</strong>BS 模型推算「目標日達目標價時權證的合理價」，固定 IV、扣除利率/股息調整。</p>
        <p><strong>權證價拆解：</strong>權證價 = <code>內含值</code> + <code>時間價值</code>，由 BS 公式自然分解。</p>
        <p><strong>損益兩平：</strong>認購 = 履約價 + 權證 / 行使比例；認售反向。</p>
        <p><strong>tick 對齊：</strong>台股升降單位（&lt; 10 → 0.01；≥ 1000 → 5 元等共 6 段）。</p>
      </div>
    </details>
  );
}

window.WAComponents3 = { ScatterChart, DetailPanel, LogicExpander };
