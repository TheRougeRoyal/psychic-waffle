import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Scatter,
  ReferenceLine, LineChart, AreaChart
} from 'recharts';

const API_BASE = 'http://localhost:8000';

const UpArrow = (props) => {
  const { cx, cy } = props;
  return <polygon points={`${cx-5},${cy+4} ${cx},${cy-4} ${cx+5},${cy+4}`} fill={props.fill || '#22c55e'} />;
};

const DownArrow = (props) => {
  const { cx, cy } = props;
  return <polygon points={`${cx-5},${cy-4} ${cx},${cy+4} ${cx+5},${cy-4}`} fill={props.fill || '#ef4444'} />;
};

const App = () => {
  // --- Control Panel State ---
  const [ticker, setTicker] = useState('AAPL');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [window, setWindow] = useState(20);
  const [stdMultiplier, setStdMultiplier] = useState(2.0);
  const [strategy, setStrategy] = useState('bollinger');
  const [riskFreeRate, setRiskFreeRate] = useState(0.0);
  const [compareMode, setCompareMode] = useState(false);
  const [selectedStrategies, setSelectedStrategies] = useState(['bollinger']);

  // --- Search State ---
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // --- Result State ---
  const [data, setData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [trades, setTrades] = useState([]);
  const [compareData, setCompareData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCached, setIsCached] = useState(false);

  // --- Debounced Search ---
  useEffect(() => {
    if (!searchQuery) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/ticker/search?q=${searchQuery}`);
        const json = await res.json();
        setSearchResults(json.slice(0, 6));
        setIsSearchOpen(true);
      } catch (e) {
        console.error("Search error", e);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const toggleStrategy = (strat) => {
    setSelectedStrategies(prev =>
      prev.includes(strat) ? prev.filter(s => s !== strat) : [...prev, strat]
    );
  };

  const handleRunBacktest = async () => {
    setIsLoading(true);
    setIsCached(false);
    setData(null);
    setMetrics(null);
    setTrades([]);
    setCompareData(null);

    try {
      if (compareMode) {
        const res = await fetch(`${API_BASE}/api/compare`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ticker,
            start_date: startDate,
            end_date: endDate,
            window,
            std_multiplier: stdMultiplier,
            risk_free_rate: parseFloat(riskFreeRate),
            strategies: selectedStrategies
          })
        });
        const json = await res.json();
        setCompareData(json);

        const firstStrat = selectedStrategies[0];
        if (firstStrat && json[firstStrat]) {
          setData(json[firstStrat].results);
          setMetrics(json[firstStrat].metrics);
          setTrades(json[firstStrat].trades);
        }
      } else {
        const res = await fetch(`${API_BASE}/api/backtest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ticker,
            start_date: startDate,
            end_date: endDate,
            window,
            std_multiplier: stdMultiplier,
            strategy,
            risk_free_rate: parseFloat(riskFreeRate)
          })
        });
        const json = await res.json();
        setData(json.results);
        setMetrics(json.metrics);
        setTrades(json.trades || []);
        setIsCached(json.cached || false);
      }
    } catch (e) {
      alert("Failed to fetch backtest data");
    } finally {
      setIsLoading(false);
    }
  };

  // --- Data Processing Helpers ---
  const buildChartData = useCallback((results) => {
    if (!results) return [];
    let cumSReturn = 0;
    let cumBnHReturn = 0;
    let runningMax = 0;

    return results.map((d, i) => {
      cumSReturn += d.strategy_return;
      if (i > 0) {
        cumBnHReturn += Math.log(d.price / results[i-1].price);
      }
      const equity = Math.exp(cumSReturn);
      const bnh = Math.exp(cumBnHReturn);
      if (equity > runningMax) runningMax = equity;
      const drawdown = (equity / runningMax) - 1;
      return {
        date: d.date,
        price: d.price,
        ma: d.ma,
        upper_band: d.upper_band,
        lower_band: d.lower_band,
        position: d.position,
        equity,
        bnh,
        drawdown
      };
    });
  }, []);

  const processedData = useMemo(() => buildChartData(data), [data, buildChartData]);

  const compareEquityData = useMemo(() => {
    if (!compareData) return [];
    const strats = Object.keys(compareData);
    if (strats.length === 0) return [];

    const firstStratData = buildChartData(compareData[strats[0]].results);

    return firstStratData.map((d, i) => {
      const row = { date: d.date };
      strats.forEach(strat => {
        const stratProcessed = buildChartData(compareData[strat].results);
        row[strat] = stratProcessed[i]?.equity || 0;
      });
      return row;
    });
  }, [compareData, buildChartData]);

  const getSignals = useCallback(() => {
    if (!data) return { buy: [], sell: [] };
    const buy = [], sell = [];
    for (let i = 1; i < data.length; i++) {
      if (data[i-1].position <= 0 && data[i].position > 0) buy.push({ ...data[i] });
      if (data[i-1].position >= 0 && data[i].position < 0) sell.push({ ...data[i] });
    }
    return { buy, sell };
  }, [data]);

  const { buy, sell } = getSignals();

  const handleExportCSV = useCallback(() => {
    if (!processedData.length) return;
    const headers = ['date', 'price', 'ma', 'upper_band', 'lower_band', 'position', 'equity', 'bnh', 'drawdown'];
    const rows = processedData.map(d => headers.map(h => d[h] !== undefined ? d[h] : '').join(','));
    const csvContent = [headers.join(','), ...rows].join('\\n').replace(/\\\\n/g, '\\n');
    // The prompt explicitly asks to fix '\\n' to '\n'.
    // In a template string or double-quoted string in JS, \n is the newline character.
    // The previous version used '\\n' which literalizes it.

    // corrected version:
    const finalCsv = [headers.join(','), ...rows].join('\\n'); // This is actually how you write it in the code if you want a literal newline in the resulting string
    // Wait, the prompt says "change '\\n' to '\n'".
    // In JS: 'a' + '\n' + 'b' is a newline. 'a' + '\\n' + 'b' is a literal backslash and n.

    // Let's be precise for the final code.
  }, [processedData, ticker, startDate, endDate]);

  // Re-implementing handleExportCSV for the final version
  const finalExportCSV = useCallback(() => {
    if (!processedData.length) return;
    const headers = ['date', 'price', 'ma', 'upper_band', 'lower_band', 'position', 'equity', 'bnh', 'drawdown'];
    const rows = processedData.map(d => headers.map(h => d[h] !== undefined ? d[h] : '').join(','));
    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${ticker}_${startDate}_${endDate}.csv`);
    link.click();
    URL.revokeObjectURL(url);
  }, [processedData, ticker, startDate, endDate]);

  // --- Inline Styles ---
  const s = {
    container: { fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#f8fafc', color: '#1e293b', minHeight: '100vh', padding: '24px', boxSizing: 'border-box' },
    card: { backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)', marginBottom: '24px' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' },
    metricCard: (isPos, isNeg) => ({
      padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0',
      backgroundColor: isPos ? '#f0fdf4' : isNeg ? '#fef2f2' : '#fff',
      borderColor: isPos ? '#bbf7d0' : isNeg ? '#fecaca' : '#e2e8f0',
      textAlign: 'center'
    }),
    metricLabel: { fontSize: '12px', color: '#64748b', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' },
    metricValue: { fontSize: '20px', fontWeight: '700', color: '#0f172a' },
    controls: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px', alignItems: 'end' },
    inputGroup: { display: 'flex', flexDirection: 'column', gap: '6px' },
    label: { fontSize: '13px', fontWeight: '500', color: '#475569' },
    input: { padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' },
    button: { padding: '10px 20px', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', fontWeight: '600', cursor: isLoading ? 'not-allowed' : 'pointer', opacity: isLoading ? 0.7 : 1 },
    exportBtn: { padding: '6px 12px', backgroundColor: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' },
    searchDropdown: { position: 'absolute', top: '100%', left: 0, right: 0, backgroundColor: 'white', border: '1px solid #e2e8f0', borderRadius: '0 0 8px 8px', zIndex: 1000, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', listStyle: 'none', padding: 0, margin: 0 },
    searchItem: { padding: '8px 12px', cursor: 'pointer', fontSize: '14px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between' },
    badge: { backgroundColor: '#f59e0b', color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '4px', marginLeft: '8px' },
    table: { width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' },
    th: { padding: '12px', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' },
    td: { padding: '12px', borderBottom: '1px solid #f1f5f9' },
    tradeBadge: (dir) => ({
      padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: '700',
      backgroundColor: dir === 'long' ? '#dcfce7' : '#fee2e2',
      color: dir === 'long' ? '#166534' : '#991b1b'
    })
  };

  const renderMetrics = () => {
    const metricIds = [
      { id: 'total_return', label: 'Total Return' },
      { id: 'annualised_return', label: 'Annualized Return' },
      { id: 'sharpe_ratio', label: 'Sharpe Ratio' },
      { id: 'max_drawdown', label: 'Max Drawdown' },
      { id: 'win_rate', label: 'Win Rate' },
      { id: 'calmar_ratio', label: 'Calmar Ratio' },
      { id: 'total_trades', label: 'Total Trades' },
      { id: 'buy_and_hold_return', label: 'B&H Return' },
    ];

    if (compareMode && compareData) {
      return (
        <div style={{ overflowX: 'auto', marginBottom: '24px' }}>
          <table style={{ ...s.table, textAlign: 'center' }}>
            <thead>
              <tr>
                <th style={s.th}>Metric</th>
                {Object.keys(compareData).map(strat => <th key={strat} style={s.th}>{strat.toUpperCase()}</th>)}
              </tr>
            </thead>
            <tbody>
              {metricIds.map(m => (
                <tr key={m.id}>
                  <td style={{ ...s.td, fontWeight: '600' }}>{m.label}</td>
                  {Object.entries(compareData).map(([strat, val]) => {
                    const v = val.metrics[m.id];
                    const isPos = v > 0;
                    const isNeg = v < 0;
                    return (
                      <td key={strat} style={{ ...s.td, color: m.id === 'total_trades' ? '#0f172a' : (isPos ? '#16a34a' : isNeg ? '#dc2626' : '#0f172a') }}>
                        {typeof v === 'number' ? (m.id === 'total_trades' ? v : `${(v * 100).toFixed(2)}%`) : v}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (metrics) {
      return (
        <div style={s.grid}>
          {metricIds.map(m => {
            const val = metrics[m.id];
            const isPos = val > 0;
            const isNeg = val < 0;
            const colorC = m.id === 'total_trades' ? null : (isPos ? 'positive' : isNeg ? 'negative' : null);
            return (
              <div key={m.id} style={s.metricCard(colorC === 'positive', colorC === 'negative')}>
                <div style={s.metricLabel}>{m.label}</div>
                <div style={s.metricValue}>
                  {typeof val === 'number' ? (m.id === 'total_trades' ? val : `${(val * 100).toFixed(2)}%`) : val}
                </div>
              </div>
            );
          })}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={s.container}>
      <div style={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '700' }}>Backtest Configuration</h2>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ fontWeight: '600' }}>{ticker}</span>
            {isCached && <span style={s.badge}>CACHED</span>}
          </div>
        </div>

        <div style={s.controls}>
          <div style={s.inputGroup}>
            <label style={s.label}>Ticker</label>
            <div style={{ position: 'relative' }}>
              <input style={s.input} value={ticker} onChange={e => { setTicker(e.target.value); setSearchQuery(e.target.value); }} />
              {isSearchOpen && (
                <ul style={s.searchDropdown}>
                  {searchResults.map((item, idx) => (
                    <li key={idx} style={s.searchItem} onClick={() => { setTicker(item.symbol); setSearchQuery(''); setIsSearchOpen(false); }}>
                      <span style={{ fontWeight: '600' }}>{item.symbol}</span>
                      <span style={{ color: '#94a3b8', fontSize: '12px' }}>{item.name}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div style={s.inputGroup}>
            <label style={s.label}>Start Date</label>
            <input type="date" style={s.input} value={startDate} onChange={e => setStartDate(e.target.value)} />
          </div>
          <div style={s.inputGroup}>
            <label style={s.label}>End Date</label>
            <input type="date" style={s.input} value={endDate} onChange={e => setEndDate(e.target.value)} />
          </div>
          <div style={s.inputGroup}>
            <label style={s.label}>Window: {window}</label>
            <input type="range" min="5" max="200" value={window} onChange={e => setWindow(parseInt(e.target.value))} />
          </div>
          <div style={s.inputGroup}>
            <label style={s.label}>Std Dev: {stdMultiplier}</label>
            <input type="range" min="0.5" max="5.0" step="0.1" value={stdMultiplier} onChange={e => setStdMultiplier(parseFloat(e.target.value))} />
          </div>

          {!compareMode ? (
            <div style={s.inputGroup}>
              <label style={s.label}>Strategy</label>
              <select style={s.input} value={strategy} onChange={e => setStrategy(e.target.value)}>
                <option value="bollinger">Bollinger</option>
                <option value="rsi">RSI</option>
                <option value="sma_cross">SMA Cross</option>
              </select>
            </div>
          ) : (
            <div style={s.inputGroup}>
              <label style={s.label}>Strategies</label>
              <div style={{ display: 'flex', gap: '10px', fontSize: '12px' }}>
                {['bollinger', 'rsi', 'sma_cross'].map(st => (
                  <label key={st} style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                    <input type="checkbox" checked={selectedStrategies.includes(st)} onChange={() => toggleStrategy(st)} />
                    {st.replace('_', ' ')}
                  </label>
                ))}
              </div>
            </div>
          )}

          <div style={s.inputGroup}>
            <label style={s.label}>Risk-Free Rate</label>
            <input type="number" style={s.input} value={riskFreeRate} onChange={e => setRiskFreeRate(e.target.value)} />
          </div>
          <div style={s.inputGroup}>
            <label style={s.label}>Mode</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input type="checkbox" checked={compareMode} onChange={() => setCompareMode(!compareMode)} />
              <span style={{ fontSize: '12px' }}>Compare</span>
            </div>
          </div>
          <button style={s.button} onClick={handleRunBacktest} disabled={isLoading}>
            {isLoading ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
      </div>

      {metrics || compareData ? (
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Performance Metrics</h3>
            <button style={s.exportBtn} onClick={finalExportCSV}>Download CSV</button>
          </div>
          {renderMetrics()}
        </div>
      ) : null}

      {data && (
        <>
          <div style={s.card}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '16px', fontWeight: '600' }}>Price Chart</h3>
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px' }} />
                  <Area type="monotone" dataKey="upper_band" stroke="none" fill="#eff6ff" fillOpacity={0.5} />
                  <Area type="monotone" dataKey="lower_band" stroke="none" fill="#fff" fillOpacity={1} />
                  <Line type="monotone" dataKey="price" stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="ma" stroke="#94a3b8" strokeWidth={1} strokeDasharray="5 5" dot={false} />
                  <Scatter data={buy} shape={<UpArrow fill="#22c55e" />} />
                  <Scatter data={sell} shape={<DownArrow fill="#ef4444" />} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={s.card}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '16px', fontWeight: '600' }}>Equity Curve</h3>
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareMode ? compareEquityData : processedData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `${((v - 1) * 100).toFixed(1)}%`} />
                  <Tooltip formatter={v => [`${((v - 1) * 100).toFixed(2)}%`, 'Return']} />
                  <ReferenceLine y={1} stroke="#cbd5e1" />
                  {!compareMode ? (
                    <>
                      <Line type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} dot={false} name="Strategy" />
                      <Line type="monotone" dataKey="bnh" stroke="#64748b" strokeWidth={1} strokeDasharray="5 5" dot={false} name="B&H" />
                    </>
                  ) : (
                    Object.entries(compareEquityData).map(([strat], idx) => (
                      <Line
                        key={strat}
                        type="monotone"
                        dataKey={strat}
                        stroke={['#10b981', '#3b82f6', '#f59e0b'][idx % 3]}
                        strokeWidth={2}
                        dot={false}
                        name={strat}
                      />
                    ))
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={s.card}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '16px', fontWeight: '600' }}>Drawdown</h3>
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={processedData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `${(v * 100).toFixed(1)}%`} />
                  <Tooltip formatter={v => [`${(v * 100).toFixed(2)}%`, 'Drawdown']} />
                  <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={s.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Trade Log</h3>
              <div style={{ fontSize: '13px', color: '#64748b' }}>
                Total Trades: {trades.length} | Win Rate: {metrics ? `${(metrics.win_rate * 100).toFixed(1)}%` : 'N/A'}
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={s.table}>
                <thead>
                  <tr>
                    <th style={s.th}>#</th>
                    <th style={s.th}>Direction</th>
                    <th style={s.th}>Entry Date</th>
                    <th style={s.th}>Entry Price</th>
                    <th style={s.th}>Exit Date</th>
                    <th style={s.th}>Exit Price</th>
                    <th style={s.th}>Return %</th>
                    <th style={s.th}>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.length > 0 ? trades.map((t, i) => (
                    <tr key={i}>
                      <td style={s.td}>{i + 1}</td>
                      <td style={s.td}><span style={s.tradeBadge(t.direction)}>{t.direction.toUpperCase()}</span></td>
                      <td style={s.td}>{t.entry_date}</td>
                      <td style={s.td}>${t.entry_price.toFixed(2)}</td>
                      <td style={s.td}>{t.exit_date}</td>
                      <td style={s.td}>${t.exit_price.toFixed(2)}</td>
                      <td style={{ ...s.td, color: t.return_pct >= 0 ? '#16a34a' : '#dc2626', fontWeight: '600' }}>
                        {(t.return_pct * 100).toFixed(2)}%
                      </td>
                      <td style={s.td}>{t.duration_days} days</td>
                    </tr>
                  )) : (
                    <tr><td colSpan="8" style={{ ...s.td, textAlign: 'center', padding: '40px' }}>No trades generated for this period.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default App;
