/* global React */
const { fmt, pct, heatBg } = window.WAComponents;
const { useState: useState2, useMemo: useMemo2 } = React;

// ============================================================
// Scenario Table
// ============================================================
function ScenarioTable({ rows }) {
  return (
    <div className="table-card">
      <div className="table-toolbar">
        <div className="table-toolbar-left">
          <input className="search" placeholder="搜尋代碼或券商…" />
          <span>顯示前 <strong style={{color:'var(--ink-1)'}}>20</strong> / 78 檔</span>
          <span className="dot-sep">·</span>
          <span>排序：達標報酬率 ↓</span>
        </div>
        <div style={{display:'flex', gap:6}}>
          <button className="btn btn-sm">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"/></svg>
            篩選
          </button>
          <button className="btn btn-sm">匯出 CSV</button>
        </div>
      </div>

      <div className="table-scroll">
        <table className="dt">
          <thead>
            <tr>
              <th className="l sticky-l" style={{minWidth:90}}>權證代碼</th>
              <th className="l sticky-l-2" style={{left:90, minWidth:130}}>權證名稱</th>
              <th>成交價</th>
              <th>等效Δ</th>
              <th>IV%</th>
              <th>槓桿</th>
              <th>履約價</th>
              <th>行使比例</th>
              <th>價內外%</th>
              <th>天期</th>
              <th>成交量</th>
              <th>損益兩平</th>
              <th>達標權證價</th>
              <th style={{background:'#fff5f1', color:'var(--up)'}}>達標報酬%</th>
              <th>平盤%</th>
              <th>跌5%</th>
              <th>跌10%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.code} className={i < 3 ? 'highlight' : ''}>
                <td className="l sticky-l code-cell">{r.code}</td>
                <td className="l sticky-l-2 name-cell" style={{left:90}}>
                  <span className="tag call" style={{marginRight:6}}>購</span>
                  {r.name}
                </td>
                <td>{fmt(r.price)}</td>
                <td>{r.delta.toFixed(3)}</td>
                <td>{r.iv.toFixed(1)}</td>
                <td>{r.lev.toFixed(2)}</td>
                <td>{fmt(r.strike, 0)}</td>
                <td>{r.ratio.toFixed(4)}</td>
                <td className={r.moneyness >= 0 ? 'up-text' : 'dim-text'}>{(r.moneyness >= 0 ? '+' : '') + r.moneyness.toFixed(1)}</td>
                <td>{r.days}</td>
                <td>{r.vol.toLocaleString()}</td>
                <td>{fmt(r.be, 0)}</td>
                <td>{fmt(r.targetPx)}</td>
                <td><span className="hm" style={heatBg(r.ret)}>+{r.ret.toFixed(1)}%</span></td>
                <td><span className="hm" style={heatBg(r.flatRet)}>{r.flatRet.toFixed(1)}%</span></td>
                <td><span className="hm" style={heatBg(r.d5)}>{r.d5.toFixed(1)}%</span></td>
                <td><span className="hm" style={heatBg(r.d10)}>{r.d10.toFixed(1)}%</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// Candidate Table
// ============================================================
function CandidateTable({ rows }) {
  const [filter, setFilter] = useState2('all');
  const filtered = filter === 'all' ? rows : rows.filter(r => r.type === filter);
  return (
    <div className="table-card">
      <div className="table-toolbar">
        <div className="table-toolbar-left">
          <input className="search" placeholder="搜尋…" />
          <span>239 檔通過硬過濾</span>
        </div>
        <div className="seg" style={{height:32, width:'auto', padding:2}}>
          <button className={filter==='all'?'active':''} onClick={()=>setFilter('all')} style={{padding:'0 12px', fontSize:12}}>全部</button>
          <button className={filter==='call'?'active up':''} onClick={()=>setFilter('call')} style={{padding:'0 12px', fontSize:12}}>認購</button>
          <button className={filter==='put'?'active down':''} onClick={()=>setFilter('put')} style={{padding:'0 12px', fontSize:12}}>認售</button>
        </div>
      </div>

      <div className="table-scroll">
        <table className="dt">
          <thead>
            <tr>
              <th className="l sticky-l" style={{minWidth:90}}>權證代碼</th>
              <th className="l sticky-l-2" style={{left:90, minWidth:140}}>權證名稱</th>
              <th>類型</th>
              <th>成交價</th>
              <th>漲跌</th>
              <th>漲跌幅</th>
              <th>成交量</th>
              <th>履約價</th>
              <th>行使比例</th>
              <th>剩餘</th>
              <th>價內外%</th>
              <th>價差比%</th>
              <th>實質槓桿</th>
              <th>隱波%</th>
              <th>等效Δ</th>
              <th>流通%</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 24).map((r) => (
              <tr key={r.code}>
                <td className="l sticky-l code-cell">{r.code}</td>
                <td className="l sticky-l-2 name-cell" style={{left:90}}>{r.name}</td>
                <td><span className={`tag ${r.type}`}>{r.type === 'call' ? '購' : '售'}</span></td>
                <td>{fmt(r.price)}</td>
                <td className={r.chg >= 0 ? 'up-text' : 'down-text'}>{(r.chg>=0?'+':'')+r.chg.toFixed(2)}</td>
                <td className={r.chgPct >= 0 ? 'up-text' : 'down-text'}>{(r.chgPct>=0?'+':'')+r.chgPct.toFixed(1)}%</td>
                <td>{r.vol.toLocaleString()}</td>
                <td>{fmt(r.strike, 0)}</td>
                <td>{r.ratio.toFixed(4)}</td>
                <td>{r.days}d</td>
                <td className={r.moneyness >= 0 ? 'up-text' : 'dim-text'}>{(r.moneyness>=0?'+':'')+r.moneyness.toFixed(1)}</td>
                <td>{r.spread.toFixed(1)}</td>
                <td>{r.lev.toFixed(2)}</td>
                <td>{r.iv.toFixed(1)}</td>
                <td>{r.delta.toFixed(3)}</td>
                <td>{r.out.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// BS Calculator
// ============================================================
function BSCalculator({ rows }) {
  const [tab, setTab] = useState2('list');
  const [selected, setSelected] = useState2(rows[0].code);
  const w = rows.find(r => r.code === selected) || rows[0];
  const [iv, setIv] = useState2(36);
  const [step, setStep] = useState2(50);
  const [r, setR] = useState2(1.5);
  const [q, setQ] = useState2(2.0);

  // Synthetic BS-ish output (cosmetic for design)
  const fair = (w.price * 0.98).toFixed(2);
  const bid = (parseFloat(fair) * 0.99).toFixed(2);
  const ask = (parseFloat(fair) * 1.01).toFixed(2);
  const dev = ((w.price - parseFloat(fair)) / parseFloat(fair) * 100);
  const intrinsic = Math.max(0, 2310 - w.strike) * w.ratio;
  const timeValue = w.price - intrinsic;

  // Sensitivity rows
  const sens = [-3,-2,-1,0,1,2,3].map(k => {
    const sPx = 2310 + k * step;
    const factor = 1 + (k * step / 2310) * w.delta * w.lev * 0.4;
    const fp = Math.max(0.01, parseFloat(fair) * factor);
    return {
      k, sPx,
      fair: fp.toFixed(2),
      bid: (fp*0.99).toFixed(2),
      ask: (fp*1.01).toFixed(2)
    };
  });

  return (
    <div className="bs-card">
      <div className="bs-head">
        <div className="left">
          <div className="icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="3" width="16" height="18" rx="2"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="8" y1="11" x2="16" y2="11"/><line x1="8" y1="15" x2="12" y2="15"/></svg>
          </div>
          合理價計算機
          <span style={{color:'var(--ink-4)', fontWeight:400, fontSize:12}}>Black-Scholes</span>
        </div>
        <div className="bs-tabs">
          <button className={tab==='list'?'active':''} onClick={()=>setTab('list')}>從候選清單選</button>
          <button className={tab==='manual'?'active':''} onClick={()=>setTab('manual')}>手動輸入</button>
        </div>
      </div>

      <div className="bs-body">
        <div className="bs-inputs">
          {tab === 'list' ? (
            <div>
              <label className="field-label">候選權證</label>
              <select className="input mono" value={selected} onChange={e=>setSelected(e.target.value)}>
                {rows.map(r => <option key={r.code} value={r.code}>{r.code} · {r.name}</option>)}
              </select>
            </div>
          ) : (
            <>
              <div className="bs-row">
                <div>
                  <label className="field-label">方向</label>
                  <div className="seg">
                    <button className="active up">認購</button>
                    <button>認售</button>
                  </div>
                </div>
                <div>
                  <label className="field-label">履約價</label>
                  <input className="input mono" defaultValue="2,500" />
                </div>
                <div>
                  <label className="field-label">行使比例</label>
                  <input className="input mono" defaultValue="0.0030" />
                </div>
              </div>
              <div className="bs-row">
                <div>
                  <label className="field-label">剩餘天數</label>
                  <input className="input mono" defaultValue="88" />
                </div>
                <div>
                  <label className="field-label">權證市價 <span className="hint">可選</span></label>
                  <input className="input mono" defaultValue="1.46" />
                </div>
                <div>
                  <label className="field-label">IV %</label>
                  <input className="input mono" defaultValue="36.0" />
                </div>
              </div>
            </>
          )}

          <div className="bs-divider"></div>

          <div className="bs-row">
            <div>
              <label className="field-label">現在標的價</label>
              <input className="input mono" defaultValue="2,310.00" />
            </div>
            <div>
              <label className="field-label">IV % <span className="slider-value mono">{iv.toFixed(1)}</span></label>
              <input type="range" min="10" max="80" step="0.5" value={iv} onChange={e=>setIv(+e.target.value)} className="slider" />
            </div>
            <div>
              <label className="field-label">敏感度步長</label>
              <input className="input mono" value={step} onChange={e=>setStep(+e.target.value)} />
            </div>
          </div>

          <div className="bs-row cols-2">
            <div>
              <label className="field-label">無風險利率 % <span className="slider-value mono">{r.toFixed(2)}</span></label>
              <input type="range" min="0" max="5" step="0.05" value={r} onChange={e=>setR(+e.target.value)} className="slider" />
            </div>
            <div>
              <label className="field-label">股息率 % <span className="slider-value mono">{q.toFixed(2)}</span></label>
              <input type="range" min="0" max="6" step="0.05" value={q} onChange={e=>setQ(+e.target.value)} className="slider" />
            </div>
          </div>
        </div>

        <div className="bs-output">
          <div className="fair-row">
            <div className="fair-cell primary">
              <div className="lbl">BS 合理價（已對齊 tick）</div>
              <div className="val tnum">{fair}</div>
              <div className="sub-line">tick = 0.01　·　模型：BS-Merton</div>
            </div>
            <div className="fair-cell">
              <div className="lbl">📥 買進可掛</div>
              <div className="val tnum" style={{color:'var(--down)'}}>{bid}</div>
              <div className="sub-line">合理價 -1 tick</div>
            </div>
            <div className="fair-cell">
              <div className="lbl">📤 賣出可掛</div>
              <div className="val tnum" style={{color:'var(--up)'}}>{ask}</div>
              <div className="sub-line">合理價 +1 tick</div>
            </div>
          </div>

          <div className="bs-meta">
            <span>市價 <strong style={{color:'var(--ink-1)'}}>{w.price.toFixed(2)}</strong></span>
            <span className="sep">·</span>
            <span>偏差 <span className={dev >= 0 ? 'pos' : 'neg'}>{dev >= 0 ? '🔴 +' : '🟢 '}{dev.toFixed(2)}%</span></span>
            <span className="sep">·</span>
            <span>內含值 <strong style={{color:'var(--ink-1)'}}>{intrinsic.toFixed(3)}</strong> + 時間價值 <strong style={{color:'var(--ink-1)'}}>{timeValue.toFixed(3)}</strong></span>
            <span className="sep">·</span>
            <span>到期 <strong style={{color:'var(--ink-1)'}}>{w.days} 天</strong></span>
          </div>

          <div style={{fontSize:11.5, color:'var(--ink-3)', marginBottom:6, textTransform:'uppercase', letterSpacing:'0.06em', fontWeight:500}}>敏感度表 · 步長 ±{step}</div>
          <table className="sens-table">
            <thead>
              <tr>
                <th className="l" style={{textAlign:'left'}}>股價變動</th>
                <th>標的價</th>
                <th>合理價</th>
                <th>買進掛</th>
                <th>賣出掛</th>
              </tr>
            </thead>
            <tbody>
              {sens.map(s => (
                <tr key={s.k} className={s.k === 0 ? 'zero' : ''}>
                  <td style={{textAlign:'left'}}>{s.k === 0 ? '0 (現價)' : `${s.k > 0 ? '+' : ''}${s.k}× = ${s.k > 0 ? '+' : ''}${(s.k*step).toLocaleString()}`}</td>
                  <td>{s.sPx.toLocaleString()}</td>
                  <td style={{color: s.k > 0 ? 'var(--up)' : s.k < 0 ? 'var(--down)' : 'var(--ink-1)', fontWeight: s.k === 0 ? 600 : 500}}>{s.fair}</td>
                  <td>{s.bid}</td>
                  <td>{s.ask}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

window.WAComponents2 = { ScenarioTable, CandidateTable, BSCalculator };
